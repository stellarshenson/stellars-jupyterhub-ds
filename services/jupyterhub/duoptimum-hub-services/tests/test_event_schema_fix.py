"""Tests for event_schema_fix.py - quoting integer event-schema versions."""

import os

from duoptimum_hub_services.event_schema_fix import fix_event_schema_versions

_SCHEMA = '''"$id": https://schema.jupyter.org/jupyterhub/events/server-action
version: {ver}
title: JupyterHub server events
type: object
'''


def _write(path, ver):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(_SCHEMA.format(ver=ver))


class TestFixEventSchemaVersions:
    def test_quotes_integer_version(self, tmp_path):
        p = str(tmp_path / "server-actions" / "v1.yaml")
        _write(p, "1")
        fixed = fix_event_schema_versions(str(tmp_path))
        assert fixed == [p]
        assert 'version: "1"' in open(p).read()

    def test_idempotent_on_already_quoted(self, tmp_path):
        p = str(tmp_path / "v1.yaml")
        _write(p, '"1"')
        before = open(p).read()
        fixed = fix_event_schema_versions(str(tmp_path))
        assert fixed == []
        assert open(p).read() == before

    def test_other_lines_untouched(self, tmp_path):
        p = str(tmp_path / "v1.yaml")
        _write(p, "2")
        fix_event_schema_versions(str(tmp_path))
        text = open(p).read()
        assert 'version: "2"' in text
        assert "title: JupyterHub server events" in text
        assert "type: object" in text

    def test_multiple_nested_files(self, tmp_path):
        a = str(tmp_path / "a" / "v1.yaml")
        b = str(tmp_path / "b" / "c" / "v2.yaml")
        _write(a, "1")
        _write(b, "3")
        fixed = fix_event_schema_versions(str(tmp_path))
        assert set(fixed) == {a, b}

    def test_empty_base_returns_empty(self, tmp_path):
        assert fix_event_schema_versions(str(tmp_path / "nope")) == []
