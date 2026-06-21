"""Tests for the loguru sink level resolution (logging_setup._resolve_level).

The sink level is driven by JUPYTERHUB_LOG_LEVEL; an operator typo must never crash the
sink at import, so anything unrecognised resolves to INFO.
"""
from duoptimum_hub_services.logging_setup import _resolve_level


class TestResolveLevel:
    def test_default_when_unset(self):
        assert _resolve_level(None) == "INFO"

    def test_blank_falls_back(self):
        assert _resolve_level("") == "INFO"
        assert _resolve_level("   ") == "INFO"

    def test_case_insensitive(self):
        assert _resolve_level("debug") == "DEBUG"
        assert _resolve_level(" Warning ") == "WARNING"

    def test_unknown_falls_back(self):
        assert _resolve_level("verbose") == "INFO"
        assert _resolve_level("42") == "INFO"

    def test_valid_levels_passthrough(self):
        for lvl in ("TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"):
            assert _resolve_level(lvl) == lvl
