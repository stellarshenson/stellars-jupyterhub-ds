"""Tests for the nvidia-smi parse logic (subprocess mocked - no GPU needed)."""

from unittest.mock import patch

from gpuinfo_nvidia import nvidia

GPU_CSV = (
    "0, NVIDIA GeForce RTX 5090, GPU-aaaa, 3, 1493, 32607\n"
    "1, NVIDIA RTX 5000 Ada, GPU-bbbb, 0, 100, 32760\n"
)
PROC_CSV = (
    "GPU-aaaa, 12345, python, 1200\n"
    "GPU-aaaa, 23456, jupyter-lab, 200\n"
)


def _fake_run(csv_gpu=GPU_CSV, csv_proc=PROC_CSV):
    def run(args, timeout=10):
        joined = " ".join(args)
        if "compute-apps" in joined:
            return csv_proc
        if "count" in joined:
            return "2\n"
        return csv_gpu
    return run


class TestSample:
    def test_parses_gpus_and_processes(self):
        with patch.object(nvidia, "_run", side_effect=_fake_run()):
            available, gpus = nvidia.sample()
        assert available is True
        assert gpus[0] == {
            "index": "0",
            "name": "NVIDIA GeForce RTX 5090",
            "uuid": "GPU-aaaa",
            "utilization": 3,
            "memory_used_mb": 1493,
            "memory_total_mb": 32607,
            "processes": [
                {"pid": 12345, "name": "python", "used_memory_mb": 1200},
                {"pid": 23456, "name": "jupyter-lab", "used_memory_mb": 200},
            ],
        }
        assert gpus[1]["uuid"] == "GPU-bbbb"
        assert gpus[1]["processes"] == []

    def test_unavailable_when_nvidia_smi_fails(self):
        with patch.object(nvidia, "_run", side_effect=Exception("no nvidia-smi")):
            available, gpus = nvidia.sample()
        assert available is False
        assert gpus == []

    def test_process_query_failure_is_non_fatal(self):
        def run(args, timeout=10):
            if "compute-apps" in " ".join(args):
                raise Exception("compute-apps unsupported")
            return GPU_CSV
        with patch.object(nvidia, "_run", side_effect=run):
            available, gpus = nvidia.sample()
        assert available is True
        assert gpus[0]["processes"] == []

    def test_process_name_with_comma_preserved(self):
        proc = "GPU-aaaa, 999, /usr/bin/python,--flag, 50\n"
        gpu = "0, NV, GPU-aaaa, 0, 0, 100\n"
        with patch.object(nvidia, "_run", side_effect=_fake_run(csv_gpu=gpu, csv_proc=proc)):
            _, gpus = nvidia.sample()
        assert gpus[0]["processes"][0]["name"] == "/usr/bin/python,--flag"
        assert gpus[0]["processes"][0]["used_memory_mb"] == 50

    def test_malformed_gpu_line_skipped(self):
        gpu = "garbage\n0, NV L4, GPU-cccc, 7, 10, 24576\n"
        with patch.object(nvidia, "_run", side_effect=_fake_run(csv_gpu=gpu, csv_proc="")):
            _, gpus = nvidia.sample()
        assert len(gpus) == 1
        assert gpus[0]["index"] == "0"
        assert gpus[0]["memory_total_mb"] == 24576


class TestDriverAvailable:
    def test_true_when_responsive(self):
        with patch.object(nvidia, "_run", return_value="2\n"):
            assert nvidia.driver_available() is True

    def test_false_when_failing(self):
        with patch.object(nvidia, "_run", side_effect=Exception()):
            assert nvidia.driver_available() is False
