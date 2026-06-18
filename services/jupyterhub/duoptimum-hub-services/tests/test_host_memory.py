"""Host RAM total readout - no-fallback memory rule.

`_host_total_memory_mb` reads /proc/meminfo and returns None on ANY failure (no
psutil fallback, no fabricated denominator). The frontend turns None into an
explicit "unavailable" state rather than guessing a host total (operator: "better
to say I don't know than guess").
"""
import builtins
import io

from duoptimum_hub_services.handlers.activity import _host_total_memory_mb


def test_reads_memtotal_from_proc_meminfo(monkeypatch):
    sample = "MemTotal:       527966636 kB\nMemFree:    1234 kB\n"
    monkeypatch.setattr(builtins, "open", lambda *a, **k: io.StringIO(sample))
    assert _host_total_memory_mb() == round(527966636 / 1024, 1)


def test_returns_none_when_meminfo_unreadable(monkeypatch):
    """No psutil fallback - a read error yields None, never a guessed value."""
    def boom(*a, **k):
        raise OSError("no /proc/meminfo")
    monkeypatch.setattr(builtins, "open", boom)
    assert _host_total_memory_mb() is None


def test_returns_none_when_memtotal_line_absent(monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda *a, **k: io.StringIO("MemFree: 100 kB\n"))
    assert _host_total_memory_mb() is None
