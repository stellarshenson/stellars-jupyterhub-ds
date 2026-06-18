"""Host CPU core-count readout - no-fallback rule (parallel to host RAM).

`_host_cpu_count` counts `processor` entries in /proc/cpuinfo and returns None on
ANY failure. It is the REAL host logical-core count - the denominator for the
Host Status "% of host" CPU bar. The frontend must divide by this, not by the
largest per-server assignment: that old approximation read ~2x high whenever every
active server was CPU-capped below the host. None turns into an explicit
"unavailable" state rather than a fabricated denominator.
"""
import builtins
import io

from duoptimum_hub_services.handlers.activity import _host_cpu_count


def test_counts_processor_lines_in_cpuinfo(monkeypatch):
    sample = (
        "processor\t: 0\nvendor_id\t: GenuineIntel\ncore id\t: 0\n\n"
        "processor\t: 1\nvendor_id\t: GenuineIntel\ncore id\t: 1\n\n"
        "processor\t: 2\nvendor_id\t: GenuineIntel\ncore id\t: 2\n\n"
        "processor\t: 3\nvendor_id\t: GenuineIntel\ncore id\t: 3\n"
    )
    monkeypatch.setattr(builtins, "open", lambda *a, **k: io.StringIO(sample))
    assert _host_cpu_count() == 4


def test_returns_none_when_cpuinfo_unreadable(monkeypatch):
    """No fallback - a read error yields None, never a guessed core count."""
    def boom(*a, **k):
        raise OSError("no /proc/cpuinfo")
    monkeypatch.setattr(builtins, "open", boom)
    assert _host_cpu_count() is None


def test_returns_none_when_no_processor_lines(monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda *a, **k: io.StringIO("vendor_id\t: GenuineIntel\n"))
    assert _host_cpu_count() is None
