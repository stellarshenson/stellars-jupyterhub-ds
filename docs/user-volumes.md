# Per-User Volumes

The platform spawns one Docker volume per user per "suffix" (`home`, `workspace`, `cache` by default). Volume names follow a fixed pattern composed at spawn time:

```
{COMPOSE_PROJECT_NAME}_jupyterlab_{username}_{suffix}
```

For example, `stellars-tech-ai-lab_jupyterlab_konrad.jelen_cache`. The compose project prefix isolates volumes when multiple deployments share the same Docker host.

## Defaults Shipped with the Image

The platform image bakes `/srv/jupyterhub/volumes_dictionary.yml` with three defaults: `home`, `workspace`, `cache`. Each entry carries the in-container mount point and the human-readable description that appears on the volume reset modal.

```yaml
home:
  mount: /home
  description: User home directory files, configurations

workspace:
  mount: /home/lab/workspace
  description: Project files, notebooks, code

cache:
  mount: /home/lab/.cache
  description: Temporary files, pip cache, conda cache
```

The runtime composes the full Docker volume name `{COMPOSE_PROJECT_NAME}_jupyterlab_{username}_{suffix}` for each entry. The flat `{name: mount}` mapping needed by `DockerSpawner` is derived automatically; the same merged structure also drives the volume reset UI labels and the bulk deletion handler.

## Operator Overlay (`JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE`)

Operators extend or override the defaults by mounting a second YAML file (same shape) into the hub container and pointing the env var at it.

**Merge rule**: per-suffix, per-field. The operator's fields win on conflict; missing fields fall back to the platform default. Suffixes only present in the overlay are added verbatim.

### Example: change a description, override a mount, add a new volume

`./user-volumes-overlay.yml` on the host:

```yaml
home:
  description: Home directory (encrypted at rest, backed up nightly)

cache:
  mount: /var/cache/lab

models:
  mount: /home/lab/models
  description: Pretrained model weights cache (rsync from shared NAS at startup)
```

`compose_override.yml`:

```yaml
services:
  jupyterhub:
    environment:
      - JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE=/srv/jupyterhub/user_volumes_overlay.yml
    volumes:
      - ./user-volumes-overlay.yml:/srv/jupyterhub/user_volumes_overlay.yml:ro
```

After restart the merged config is:

| Suffix | Mount | Description |
|---|---|---|
| `home` | `/home` (default) | Home directory (encrypted at rest, backed up nightly) (overlay) |
| `workspace` | `/home/lab/workspace` (default) | Project files, notebooks, code (default) |
| `cache` | `/var/cache/lab` (overlay) | Temporary files, pip cache, conda cache (default) |
| `models` | `/home/lab/models` (overlay) | Pretrained model weights cache (overlay only) |

### Example: minimal overlay (description-only)

```yaml
workspace:
  description: Notebooks, datasets, results - DO NOT store credentials here
```

Only the workspace description is overridden; mount stays at the platform default. Other suffixes are untouched.

## Reset UI Behaviour

Both `home.html` (user self-service) and `admin.html` (admin manage-volumes modal) iterate the merged list and show, per row, the suffix, the full Docker volume name (with `{username}` substituted), and the description. The bulk delete handler `ManageVolumesHandler.delete` pulls the same name templates from `tornado_settings.stellars_config['user_volume_name_templates']` so UI labels and on-disk volume names cannot drift.

When you add a custom suffix via the overlay, it appears as an additional checkbox in both reset modals automatically; no template changes required.

## File Reference

| Path | Purpose |
|---|---|
| `/srv/jupyterhub/volumes_dictionary.yml` | Platform defaults baked into the image |
| Path of `JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE` | Operator overlay (optional, mounted at deploy time) |
| `services/jupyterhub/stellars_hub/stellars_hub/volumes.py::load_merged_user_volumes` | Loader + per-field merger |
| `config/jupyterhub_config.py::USER_VOLUMES` | Final merged dict, keyed by full pattern with `{username}` placeholder |
