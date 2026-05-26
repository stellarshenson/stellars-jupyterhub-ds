"""Functional tests for gpu.py - GPU enumeration and resolve_gpu_mode logic.

The hub has no GPU access of its own, so detection/enumeration run an ephemeral
CUDA container (runtime=nvidia) and parse nvidia-smi's CSV output. resolve_gpu_mode
returns (gpu_enabled, nvidia_detected, gpu_list); detection is derived from the
enumeration so a single container run serves both.
"""

from unittest.mock import patch

from stellars_hub_services.gpu import enumerate_gpus, resolve_gpu_mode


class TestResolveGpuMode:
    def test_mode_0_disabled(self):
        """Mode 0 returns (0, 0, []) without touching the GPU container."""
        with patch("stellars_hub_services.gpu.enumerate_gpus") as mock_enum:
            result = resolve_gpu_mode(0, "nvidia/cuda:test")
        assert result == (0, 0, [])
        mock_enum.assert_not_called()

    def test_mode_1_enabled_enumerates(self):
        """Mode 1 (forced) stays on AND enumerates via the ephemeral container."""
        gpus = [{"index": "0", "name": "NVIDIA L4", "uuid": "GPU-x", "memory_mb": 24576}]
        with patch("stellars_hub_services.gpu.enumerate_gpus", return_value=gpus) as mock_enum:
            result = resolve_gpu_mode(1, "nvidia/cuda:test")
        assert result == (1, 1, gpus)
        mock_enum.assert_called_once_with("nvidia/cuda:test")

    def test_mode_1_enabled_stays_on_when_no_gpus(self):
        """Mode 1 forced grant stays on even if enumeration finds nothing."""
        with patch("stellars_hub_services.gpu.enumerate_gpus", return_value=[]) as mock_enum:
            result = resolve_gpu_mode(1, "nvidia/cuda:test")
        assert result == (1, 0, [])
        mock_enum.assert_called_once_with("nvidia/cuda:test")

    def test_mode_2_autodetect_found(self):
        """Mode 2 + GPUs found returns (1, 1, gpu_list)."""
        gpus = [{"index": "0", "name": "NVIDIA A100", "uuid": "GPU-a", "memory_mb": 81920}]
        with patch("stellars_hub_services.gpu.enumerate_gpus", return_value=gpus) as mock_enum:
            result = resolve_gpu_mode(2, "nvidia/cuda:test")
        assert result == (1, 1, gpus)
        mock_enum.assert_called_once_with("nvidia/cuda:test")

    def test_mode_2_autodetect_not_found(self):
        """Mode 2 + no GPUs returns (0, 0, [])."""
        with patch("stellars_hub_services.gpu.enumerate_gpus", return_value=[]) as mock_enum:
            result = resolve_gpu_mode(2, "nvidia/cuda:test")
        assert result == (0, 0, [])
        mock_enum.assert_called_once_with("nvidia/cuda:test")


class TestEnumerateGpus:
    def test_parses_nvidia_smi_csv(self):
        sample = (
            b"0, NVIDIA A100-SXM4-80GB, GPU-aaaa, 81920 MiB\n"
            b"1, NVIDIA A100-SXM4-80GB, GPU-bbbb, 81920 MiB\n"
        )
        with patch("docker.DockerClient") as mock_cls:
            mock_cls.return_value.containers.run.return_value = sample
            gpus = enumerate_gpus("nvidia/cuda:test")
        assert gpus == [
            {"index": "0", "name": "NVIDIA A100-SXM4-80GB", "uuid": "GPU-aaaa", "memory_mb": 81920},
            {"index": "1", "name": "NVIDIA A100-SXM4-80GB", "uuid": "GPU-bbbb", "memory_mb": 81920},
        ]

    def test_empty_on_run_error(self):
        with patch("docker.DockerClient") as mock_cls:
            mock_cls.return_value.containers.run.side_effect = Exception("no nvidia runtime")
            assert enumerate_gpus("nvidia/cuda:test") == []

    def test_empty_on_client_error(self):
        with patch("docker.DockerClient", side_effect=Exception("docker unreachable")):
            assert enumerate_gpus("nvidia/cuda:test") == []

    def test_malformed_line_skipped(self):
        sample = b"garbage line\n0, NVIDIA L4, GPU-cccc, 24576 MiB\n"
        with patch("docker.DockerClient") as mock_cls:
            mock_cls.return_value.containers.run.return_value = sample
            gpus = enumerate_gpus("nvidia/cuda:test")
        assert gpus == [
            {"index": "0", "name": "NVIDIA L4", "uuid": "GPU-cccc", "memory_mb": 24576},
        ]
