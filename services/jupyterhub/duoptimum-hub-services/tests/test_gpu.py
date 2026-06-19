"""Functional tests for gpu.py - GPU enumeration and resolve_gpu_mode logic.

The hub has no GPU access of its own, so detection/enumeration query the
gpuinfo-nvidia sidecar over HTTP (see gpu_client) instead of spawning a CUDA
container. resolve_gpu_mode returns (gpu_enabled, nvidia_detected, gpu_list);
detection is derived from the inventory so one sidecar serves both.
"""

from unittest.mock import patch

from duoptimum_hub_services.gpu import enumerate_gpus, gpu_summary_lines, resolve_gpu_mode


def _payload(gpus):
    return {"vendor": "nvidia", "available": bool(gpus), "count": len(gpus), "gpus": gpus, "timestamp": "t"}


class TestResolveGpuMode:
    def test_mode_0_off(self):
        """Mode 0 (off) returns (0, 0, []) without touching the sidecar."""
        with patch("duoptimum_hub_services.gpu.enumerate_gpus") as mock_enum:
            result = resolve_gpu_mode(0)
        assert result == (0, 0, [])
        mock_enum.assert_not_called()

    def test_mode_1_autodetect_found(self):
        """Mode 1 (autodetect, the default) turns GPU on iff GPUs are found."""
        gpus = [{"index": "0", "name": "NVIDIA L4", "uuid": "GPU-x", "memory_mb": 24576}]
        with patch("duoptimum_hub_services.gpu.enumerate_gpus", return_value=gpus) as mock_enum:
            result = resolve_gpu_mode(1)
        assert result == (1, 1, gpus)
        mock_enum.assert_called_once_with()

    def test_mode_1_autodetect_off_when_no_gpus(self):
        """No "forced on": autodetect with an empty inventory resolves to off - the
        platform never claims GPUs it cannot back."""
        with patch("duoptimum_hub_services.gpu.enumerate_gpus", return_value=[]) as mock_enum, \
             patch("duoptimum_hub_services.gpu.load_cached", return_value=None):
            result = resolve_gpu_mode(1)
        assert result == (0, 0, [])
        mock_enum.assert_called_once_with()

    def test_legacy_mode_2_treated_as_autodetect(self):
        """The legacy value 2 (old explicit autodetect) still autodetects, so existing
        deployments keep working."""
        gpus = [{"index": "0", "name": "NVIDIA A100", "uuid": "GPU-a", "memory_mb": 81920}]
        with patch("duoptimum_hub_services.gpu.enumerate_gpus", return_value=gpus) as mock_enum:
            result = resolve_gpu_mode(2)
        assert result == (1, 1, gpus)
        mock_enum.assert_called_once_with()


class TestEnumerateGpus:
    def test_maps_sidecar_payload(self):
        gpus = [
            {"index": "0", "name": "NVIDIA A100-SXM4-80GB", "uuid": "GPU-aaaa",
             "utilization": 3, "memory_used_mb": 100, "memory_total_mb": 81920, "processes": []},
            {"index": "1", "name": "NVIDIA A100-SXM4-80GB", "uuid": "GPU-bbbb",
             "utilization": 0, "memory_used_mb": 0, "memory_total_mb": 81920, "processes": []},
        ]
        with patch("duoptimum_hub_services.gpu_client.fetch_payload_with_retry", return_value=_payload(gpus)):
            result = enumerate_gpus()
        assert result == [
            {"index": "0", "name": "NVIDIA A100-SXM4-80GB", "uuid": "GPU-aaaa", "memory_mb": 81920},
            {"index": "1", "name": "NVIDIA A100-SXM4-80GB", "uuid": "GPU-bbbb", "memory_mb": 81920},
        ]

    def test_empty_when_sidecar_unreachable(self):
        with patch("duoptimum_hub_services.gpu_client.fetch_payload_with_retry", return_value=None):
            assert enumerate_gpus() == []

    def test_empty_when_no_gpus_reported(self):
        with patch("duoptimum_hub_services.gpu_client.fetch_payload_with_retry", return_value=_payload([])):
            assert enumerate_gpus() == []

    def test_legacy_image_arg_ignored(self):
        """Existing callers passing the old CUDA-image arg still work."""
        with patch("duoptimum_hub_services.gpu_client.fetch_payload_with_retry", return_value=_payload([])):
            assert enumerate_gpus("nvidia/cuda:test") == []

    def test_entry_missing_index_skipped(self):
        gpus = [{"name": "ghost", "memory_total_mb": 1}, {"index": "0", "name": "NV", "uuid": "u", "memory_total_mb": 24576}]
        with patch("duoptimum_hub_services.gpu_client.fetch_payload_with_retry", return_value=_payload(gpus)):
            result = enumerate_gpus()
        assert result == [{"index": "0", "name": "NV", "uuid": "u", "memory_mb": 24576}]


class TestGpuSummaryLines:
    def test_caps_and_full_health(self):
        gpus = [{"index": "0", "name": "NVIDIA L4", "uuid": "GPU-x", "utilization": 42,
                 "memory_used_mb": 4096, "memory_total_mb": 24576, "temperature_c": 55, "power_w": 70.0}]
        with patch("duoptimum_hub_services.gpu_client.fetch_payload_with_retry", return_value=_payload(gpus)):
            lines = gpu_summary_lines()
        assert lines == ["GPU 0: NVIDIA L4 (24 GB) - 42% util, 4.0/24 GB, 55 C, 70 W"]

    def test_omits_missing_metrics_never_none(self):
        # only capabilities + utilisation reported; temp/power/used absent -> omitted
        gpus = [{"index": "0", "name": "NV", "memory_total_mb": 24576, "utilization": 0}]
        with patch("duoptimum_hub_services.gpu_client.fetch_payload_with_retry", return_value=_payload(gpus)):
            lines = gpu_summary_lines()
        assert lines == ["GPU 0: NV (24 GB) - 0% util"]
        assert "None" not in lines[0]

    def test_empty_when_unreachable(self):
        with patch("duoptimum_hub_services.gpu_client.fetch_payload_with_retry", return_value=None):
            assert gpu_summary_lines() == []
