# JupyterHub Configuration

The hub container ships a working built-in `jupyterhub_config.py`. Operators can override it without rebuilding the image by dropping their own file(s) into a host directory and bind-mounting it at `/mnt/user_config`.

| Path | Role |
|---|---|
| `/mnt/user_config` | Operator-supplied python files (optional bind-mount, ro). The root file's name defaults to `jupyterhub_config.py` (overridable via `JUPYTERHUB_USER_CONFIG_FILE`). |
| `/srv/jupyterhub/jupyterhub_config.py` | Built-in default baked into the image. Untouched at runtime. |
| `/srv/config/` | Runtime location JupyterHub actually loads. Repopulated every boot from one of the two sources above. |

On startup, `01_provision_config.sh` decides what JupyterHub will load:

| `/mnt/user_config/<root>` | Action | Source |
|---|---|---|
| missing (or `/mnt/user_config` absent / empty) | copy `/srv/jupyterhub/jupyterhub_config.py` -> `/srv/config/jupyterhub_config.py` | built-in |
| present, non-empty, `py_compile` passes | wipe `/srv/config/`, `cp -a /mnt/user_config/. /srv/config/` | operator-supplied |
| present but **empty** | log error, **exit 1** (boot fails) | — |
| present but **syntax error** | log error with `py_compile` output, **exit 1** | — |

Re-runs every boot so operator edits to files under `/mnt/user_config` take effect on the next container restart, and a previous overlay does not linger after the operator removes the bind-mount. Server files in `/srv/jupyterhub/` (built-in config, dictionaries, templates) are never written to.

## Supplying your own config

In your deployment overlay's `compose_override.yml`:

```yaml
services:
  jupyterhub:
    volumes:
      - ./my_config:/mnt/user_config:ro
```

Inside `./my_config/` on the host:

```
my_config/
  jupyterhub_config.py   # required: the root file
  helpers.py             # optional: any sibling .py is copied alongside
  custom_auth.py         # optional: ditto
```

The root file is loaded by JupyterHub directly. Sibling files are copied to `/srv/config/` and are importable from the root — `PYTHONPATH=/srv/config` is set in the image so `from helpers import foo` works without further setup.

## Renaming the root file

If you want a name other than `jupyterhub_config.py`, set `JUPYTERHUB_USER_CONFIG_FILE` in the hub environment:

```yaml
services:
  jupyterhub:
    environment:
      - JUPYTERHUB_USER_CONFIG_FILE=my_hub_config.py
    volumes:
      - ./my_config:/mnt/user_config:ro
```

The provisioning script reads the override, validates `/mnt/user_config/my_hub_config.py`, copies all overlay files to `/srv/config/`, and additionally writes a same-content copy as `/srv/config/jupyterhub_config.py` so the JupyterHub launch command stays uniform.

## What does NOT get overridden

The overlay only steers which `jupyterhub_config.py` JupyterHub loads. It does **not** override server-side files in `/srv/jupyterhub/`:

- `settings_dictionary.yml` (Settings page schema)
- `volumes_dictionary.yml` (user-volume defaults — use `JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE` for that overlay; see `docs/user-volumes.md`)
- HTML templates under `/srv/jupyterhub/templates/`

Dropping any of those filenames into `/mnt/user_config/` copies them to `/srv/config/` (no harm, no effect) — JupyterHub only reads them from `/srv/jupyterhub/`.

## Failure modes

- **Empty file**: `/mnt/user_config/jupyterhub_config.py` is 0 bytes. Boot fails with `[Config] ERROR: /mnt/user_config/jupyterhub_config.py is empty`.
- **Syntax error**: `python3 -m py_compile` rejects the file. Boot fails with the compile output followed by `[Config] ERROR: ... failed py_compile`.

Both cases are intentional — silently falling back to the built-in would mask operator typos and cause confusing behavior changes on restart. Fix the file (or remove it to opt out of the overlay) and restart.
