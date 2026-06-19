"""Build-time fix: quote the integer ``version:`` in JupyterHub's bundled event schemas.

``jupyter_events >= 0.11`` requires an event schema's ``version`` to be a string; upstream
JupyterHub still ships ``version: 1`` (int) in its ``event-schemas/*.yaml``, which logs a
``JupyterEventsVersionWarning`` on every hub start. This rewrites those files in place so
the schemas validate cleanly. Idempotent and stdlib-only; run once at image build time
(see ``Dockerfile.jupyterhub``) where jupyterhub is installed.
"""

import glob
import os
import re

# matches a top-level `version:` whose value is an unquoted integer (the whole line)
_VERSION_LINE = re.compile(r'^(version:[ \t]*)(\d+)[ \t]*$', re.M)


def jupyterhub_event_schemas_dir():
    """Path to JupyterHub's bundled event-schemas directory."""
    import jupyterhub
    return os.path.join(os.path.dirname(jupyterhub.__file__), 'event-schemas')


def fix_event_schema_versions(base=None):
    """Quote unquoted integer ``version:`` in every event-schema YAML under ``base``
    (JupyterHub's bundled dir when None). Returns the list of files changed and prints
    a one-line summary so the build log shows what was configured."""
    base = base or jupyterhub_event_schemas_dir()
    paths = sorted(glob.glob(os.path.join(base, '**', '*.yaml'), recursive=True))
    fixed = []
    for path in paths:
        with open(path) as f:
            text = f.read()
        new = _VERSION_LINE.sub(r'\1"\2"', text)
        if new != text:
            with open(path, 'w') as f:
                f.write(new)
            fixed.append(path)
            print(f"[event-schema-fix] quoted version in {path}", flush=True)
    print(
        f"[event-schema-fix] {len(paths)} schema(s) under {base}; "
        f"{len(fixed)} fixed, {len(paths) - len(fixed)} already a string",
        flush=True,
    )
    return fixed
