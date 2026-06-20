# Acceptance Criteria - Lab name branding env rename

The hub knob `JUPYTERLAB_SYSTEM_NAME` is renamed to `JUPYTERHUB_BRANDING_LAB_NAME` (consistent with the `JUPYTERHUB_BRANDING_*` family); the hub injects it into every spawned lab as `JUPYTERLAB_SYSTEM_NAME` - the var the lab image consumes for its header, welcome page and MOTD. The two fine-grained header envs `JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME` and `JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR` are dropped: capitalization by typing the name in caps, header colour moves to Settings.

## Rename

- [x] **Hub knob renamed** - `JUPYTERHUB_BRANDING_LAB_NAME` replaces the hub-side `JUPYTERLAB_SYSTEM_NAME` in Dockerfile ENV, compose.yml, settings_dictionary.yml and the config read
  - log: 2026-06-20 implemented (Dockerfile, compose.yml, settings_dictionary.yml, config/jupyterhub_config.py)
- [x] **Injected as JUPYTERLAB_SYSTEM_NAME** - the hub forwards `JUPYTERHUB_BRANDING_LAB_NAME` into each spawned lab as `JUPYTERLAB_SYSTEM_NAME`; the lab image is unchanged (still consumes `JUPYTERLAB_SYSTEM_NAME`)
  - log: 2026-06-20 implemented - `c.DockerSpawner.environment['JUPYTERLAB_SYSTEM_NAME'] = JUPYTERHUB_BRANDING_LAB_NAME`
- [x] **Stays reserved** - `JUPYTERLAB_SYSTEM_NAME` remains in `RESERVED_ENV_VAR_NAMES` (auto from the spawner-env keys) so groups cannot override it
  - log: 2026-06-20 confirmed - reserved set derives from `c.DockerSpawner.environment.keys()`
- [x] **Default empty** - `JUPYTERHUB_BRANDING_LAB_NAME` default empty (Dockerfile + settings dict); empty = no rebrand
  - log: 2026-06-20 implemented

## Drop

- [x] **Capitalize env dropped** - `JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME` removed from Dockerfile, compose.yml, settings_dictionary.yml, the config read AND the spawner env (no longer set on the lab container)
  - log: 2026-06-20 implemented (operator: capitalize by typing the name in caps)
- [x] **Color env dropped** - `JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR` removed from the same five places and the spawner env
  - log: 2026-06-20 implemented (operator: header colour moves to Settings)
- [ ] **Edge: not on the container** - a spawned lab's `Config.Env` contains neither `JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME` nor `JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR`
  - log: 2026-06-20 criterion added; functional assertion (needs rebuild run)

## Verification

- [ ] **Functional test** - on the rebuilt image, a spawned lab's `Config.Env` has `JUPYTERLAB_SYSTEM_NAME` = the configured `JUPYTERHUB_BRANDING_LAB_NAME` value, and neither dropped env is present
  - log: 2026-06-20 criterion added; test written (`test_lab_name_branding.py`), functest hub sets `JUPYTERHUB_BRANDING_LAB_NAME=Functest Lab Name`; needs operator rebuild run
- [x] **No dangling references** - no code/config/doc in active files references the old hub-side `JUPYTERLAB_SYSTEM_NAME` read or the two dropped envs (CHANGELOG/JOURNAL history excepted)
  - log: 2026-06-20 grep-confirmed across config/Dockerfile/compose/settings_dictionary/README/architecture
