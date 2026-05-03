# Config

Image has built-in `jupyterhub_config.py`. Want different one? Put it in `./config/`. Done.

## Paths

| Where | What |
|---|---|
| `./config/` (host) | Your stuff. Optional. |
| `/mnt/user_config` (container) | Same dir. Read-only bind. |
| `/srv/jupyterhub/jupyterhub_config.py` | Built-in. Baked in. Never overwritten. |
| `/srv/config/` | Live config. Rebuilt every boot. |

## Rules

| `./config/jupyterhub_config.py` | Result |
|---|---|
| Missing | Built-in used. |
| Present, valid | Yours used. Helpers come along. |
| Present, empty | Boot fails. Exit 1. |
| Present, syntax broken | Boot fails. Exit 1. Stack trace logged. |

No silent fallback on broken file. Operator typo, boot dies. Loud.

## Helpers

```
./config/
  jupyterhub_config.py   ← required
  helpers.py             ← optional
  auth.py                ← optional
```

Siblings copied. Importable. `PYTHONPATH=/srv/config` baked in.

## Rename root

Set env. Default name is `jupyterhub_config.py`.

```yaml
services:
  jupyterhub:
    environment:
      - JUPYTERHUB_USER_CONFIG_FILE=my_hub_config.py
```

## Different host folder

Override the bind:

```yaml
services:
  jupyterhub:
    volumes:
      - ../config:/mnt/user_config:ro
```

## What is not overridden

Server files. Stay at `/srv/jupyterhub/`. Hub reads them from there.

- `settings_dictionary.yml`
- `volumes_dictionary.yml` (use `JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE` overlay; see [user-volumes.md](user-volumes.md))
- HTML templates

Drop those filenames into `./config/`? Copied to `/srv/config/`. Ignored. Hub reads from `/srv/jupyterhub/`.

## Edits and restarts

Every boot wipes `/srv/config/` and re-copies. Edit a file in `./config/`. Restart container. Picked up.

Remove `./config/`. Restart. Built-in used. No leftovers.

## Failures

Empty file:

```
[Config] ERROR: /mnt/user_config/jupyterhub_config.py is empty
```

Syntax broken:

```
SyntaxError: ...
[Config] ERROR: /mnt/user_config/jupyterhub_config.py failed syntax check (see above)
```

Fix file. Restart. Or remove file to use built-in.
