# Acceptance Criteria - Lab Setup: system volumes panel

The Lab Setup page shows the spawn image and the standard per-user lab volumes (workspace/home/cache from `volumes_dictionary.yml`). Add a second panel for the platform system volumes - the shared volume and the docker-proxy volume - read from their docker `duoptimum-hub.volume.*` labels (not the lab volumes file), with where each mounts into a lab and a note that access is policy-controlled.

## Lab volumes (existing, unchanged)

- [x] **Lab image** - shows `JUPYTERHUB_LAB_IMAGE`, deployment-set tooltip
  - log: 2026-06-20 pre-existing
- [x] **Standard Volumes table** - Name / Mount Point / Description for workspace, home, cache from `volumes_dictionary.yml`
  - log: 2026-06-20 pre-existing
- [x] **Scope: lab volumes file stays lab-only** - `volumes_dictionary.yml` keeps only the key per-user lab volumes (workspace/home/cache); system volumes are NOT added to it
  - log: 2026-06-20 criterion added (operator: "volume description file keeps only description about key lab volumes")
  - log: 2026-06-20 confirmed - `volumes_dictionary.yml` untouched; system volumes resolved from docker labels at config-load

## System volumes panel (new)

- [x] **Panel present** - a "System Volumes" panel below Standard Volumes, same table shape (Name / Mount Point / Description)
  - log: 2026-06-20 implemented (`LabContainer.tsx`); functional verify pending rebuild run
- [x] **Shared volume row** - name = resolved `JUPYTERHUB_SHARED_VOLUME_NAME` (by `duoptimum-hub.volume.role=shared`), mount = `/mnt/shared`, description = its `duoptimum-hub.volume.description` label
  - log: 2026-06-20 implemented - `build_system_volume_rows` row from `(JUPYTERHUB_SHARED_VOLUME_NAME, SHARED_MOUNTPOINT, shared-role)`
- [x] **Docker-proxy volume row** - name = resolved docker-proxy sockets volume (by `duoptimum-hub.volume.role`=docker-proxy), mount = `/run/dockersock` (per-user subpath), description = its `duoptimum-hub.volume.description` label
  - log: 2026-06-20 implemented - row from `(JUPYTERHUB_DOCKER_PROXY_SOCKETS_VOLUME, SOCK_MOUNT_DIR, docker-proxy-role)`
- [x] **Descriptions from labels** - system-volume descriptions come from the docker `duoptimum-hub.volume.description` labels, resolved server-side; never from `volumes_dictionary.yml`
  - log: 2026-06-20 implemented - `volume_labels(name)[<role-key-prefix>.description]`, read at config-load
- [x] **Policy note** - a notice on the panel: access to the system volumes is controlled via group policies (shared -> shared-volume grant; docker-proxy -> docker-access grant), pointing to the per-group Volume mounts section
  - log: 2026-06-20 implemented - `Notice` shown with the panel; generic per-group grant note retained below

## Edge cases

- [x] **Edge: shared volume absent** - shared not resolved in this namespace -> omit the shared row (no blank/placeholder)
  - log: 2026-06-20 implemented + unit-tested (`test_shared_absent_row_omitted`) - empty name skipped in builder
- [x] **Edge: docker-proxy volume absent** - proxy volume not resolved -> omit the docker-proxy row
  - log: 2026-06-20 implemented + unit-tested (`test_proxy_absent_row_omitted`)
- [x] **Edge: label missing** - volume present but no `duoptimum-hub.volume.description` label -> row shows name + mount, description blank (not an error)
  - log: 2026-06-20 implemented + unit-tested (`test_volume_present_but_label_missing_blank_description`, `test_volume_missing_blank_description`)
- [x] **Edge: both absent** - no system volumes resolved -> panel hidden, never a half-empty table
  - log: 2026-06-20 implemented - `{systemVolumes.length > 0 && ...}` hides the panel + the policy note; builder returns `[]` (unit-tested `test_both_absent_empty`)

## API / data

- [x] **Payload** - system volumes delivered inside the existing `GET /activity` snapshot as `system_volumes: [{name, mount, description, role}]` (admin), built at config-load into `stellars_config`; `getLabContainer` maps them onto `LabContainerInfo.systemVolumes`
  - log: 2026-06-20 implemented - `stellars_config['system_volumes']` (config) -> `ActivityDataHandler` response -> `liveSource.getLabContainer` -> `LabContainerInfo.systemVolumes`

## Verification

- [x] **Unit tests** - config-load builder produces the shared + docker-proxy rows from resolved names + labels; omits absent volumes; blank description when label missing
  - log: 2026-06-20 green - `build_system_volume_rows` extracted to `docker_utils` (pure, label-reader injected); 9 scenario tests in `test_system_volume_rows.py`; backend suite 863 passed; frontend typecheck + lint clean
- [x] **Functional test** - Lab Setup page shows the System Volumes panel with the shared + docker-proxy rows (name/mount/description) and the policy note, on the rebuilt image
  - log: 2026-06-20 criterion added; tests written (`test_lab_setup_system_volumes.py`: `/activity` payload + UI panel); functest volumes given `duoptimum-hub.volume.description` labels; needs operator rebuild run
  - log: 2026-06-20 PASS - rebuilt image, signup regime: `test_system_volumes_in_activity` (shared + docker-proxy rows, mounts, descriptions from labels) + `test_lab_setup_page_shows_system_volumes_panel` (both panels, description text, policy note) green
