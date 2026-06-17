# Acceptance Criteria - version sync across subpackages

`make increment_version` bumps the patch version of the root project and every in-repo package baked into the hub image in lockstep, by setting the new version absolutely (not matching the old string) so a drifted subpackage is pulled back into sync rather than skipped.

- [x] **Root + three subpackages** - sets the version on `pyproject.toml`, `optimum-hub-web/pyproject.toml`, `stellars-hub-services/pyproject.toml`, `stellars-docker-proxy/pyproject.toml`, and `optimum-hub-web/package.json`
  - log: 2026-06-17 `VERSIONED_PYPROJECTS` loop + package.json sed; `Makefile`
- [x] **Image packages only** - the three subpackages are exactly the wheels the hub image installs (Dockerfile lines 174-176); `optimum hub`, `jupyter hub services`, and `the other one` = docker-proxy
  - log: 2026-06-17 confirmed against `Dockerfile.jupyterhub`
- [x] **gpuinfo-nvidia excluded** - the GPU-info sidecar is a separate image with its own version; intentionally not synced
  - log: 2026-06-17 left at its own version, documented in the Makefile comment
- [x] **Absolute set fixes drift** - uses `s/^version = "[^"]*"$/.../` so hub-services (was 3.8.0) and any drifted package jump to the new root version, not just packages already in sync
  - log: 2026-06-17 prior recipe matched the old string and silently skipped drifted packages
- [x] **Single version line** - each pyproject has exactly one `[project] version` line and package.json one `"version"`, so the absolute sed touches only the intended line
  - log: 2026-06-17 verified before changing the recipe
- [x] **Edge: no helper script** - manifest set is an inline Make variable + a bash `for` loop in the recipe, no external script
  - log: 2026-06-17 per the inline-metadata convention
