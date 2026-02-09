"""Functional tests for gpu.py - resolve_gpu_mode logic."""

from unittest.mock import patch

from stellars_hub.gpu import resolve_gpu_mode


class TestResolveGpuMode:
    def test_mode_0_disabled(self):
        """Mode 0 returns (0, 0), detect_nvidia not called."""
        with patch("stellars_hub.gpu.detect_nvidia") as mock_detect:
            result = resolve_gpu_mode(0, "nvidia/cuda:test")

        assert result == (0, 0)
        mock_detect.assert_not_called()

    def test_mode_1_enabled(self):
        """Mode 1 returns (1, 0), detect_nvidia not called."""
        with patch("stellars_hub.gpu.detect_nvidia") as mock_detect:
            result = resolve_gpu_mode(1, "nvidia/cuda:test")

        assert result == (1, 0)
        mock_detect.assert_not_called()

    def test_mode_2_autodetect_found(self):
        """Mode 2 + GPU found returns (1, 1)."""
        with patch("stellars_hub.gpu.detect_nvidia", return_value=1) as mock_detect:
            result = resolve_gpu_mode(2, "nvidia/cuda:test")

        assert result == (1, 1)
        mock_detect.assert_called_once_with("nvidia/cuda:test")

    def test_mode_2_autodetect_not_found(self):
        """Mode 2 + GPU not found returns (0, 0)."""
        with patch("stellars_hub.gpu.detect_nvidia", return_value=0) as mock_detect:
            result = resolve_gpu_mode(2, "nvidia/cuda:test")

        assert result == (0, 0)
        mock_detect.assert_called_once_with("nvidia/cuda:test")
