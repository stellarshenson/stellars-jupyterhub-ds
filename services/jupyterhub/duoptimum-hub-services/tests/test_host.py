"""Tests for host-resource calculation helpers (duoptimum_hub_services.host).

`resolve_memory_quota_mb` was extracted verbatim from jupyterhub_config.py (it is
pure calculation, so it belongs in the package); these lock in its behaviour.
"""

import builtins
import io

from duoptimum_hub_services.host import resolve_memory_quota_mb


def test_resolve_memory_quota_mb_reads_meminfo(monkeypatch):
    real_open = builtins.open
    meminfo = "MemTotal:        8388608 kB\nMemFree:          100 kB\n"  # 8 GiB total

    def fake_open(path, *a, **k):
        if path == '/proc/meminfo':
            return io.StringIO(meminfo)
        return real_open(path, *a, **k)

    monkeypatch.setattr(builtins, "open", fake_open)
    # 8388608 kB / 1024 = 8192 MB; * 0.25 = 2048 MB
    assert resolve_memory_quota_mb(0.25) == 2048


def test_resolve_memory_quota_mb_fallback_on_error(monkeypatch):
    real_open = builtins.open

    def fake_open(path, *a, **k):
        if path == '/proc/meminfo':
            raise OSError("unreadable")
        return real_open(path, *a, **k)

    monkeypatch.setattr(builtins, "open", fake_open)
    assert resolve_memory_quota_mb(0.25) == 4096  # 4 GB fallback


def test_resolve_memory_quota_mb_returns_positive_int():
    # On any host (real /proc/meminfo or the fallback) the result is a positive int.
    val = resolve_memory_quota_mb(0.25)
    assert isinstance(val, int) and val > 0
