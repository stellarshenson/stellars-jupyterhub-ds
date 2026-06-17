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
- [x] **package-lock.json tracks the bump** - `increment_version` also rewrites the lockfile's own version (root `.version` + `packages[""].version`) so it never drifts from package.json; the image build runs `npm ci` (`Dockerfile.jupyterhub:61`) which aborts with EUSAGE on a package.json/lock version mismatch
  - log: 2026-06-17 found via adversarial review - the prior recipe bumped package.json only, leaving the lockfile at 4.0.0 while package.json was 4.0.1 (a committed build-breaker); fixed with an `awk` first-two-`"version"`-fields rewrite + a one-time lockfile resync
- [x] **Edge: transitive deps named like the project version** - the lockfile holds many `"version"` lines; the bump targets only the first two (root + `packages[""]`, always the first two in lockfileVersion 3) so a transitive dep that happens to share the project version is not corrupted
  - log: 2026-06-17 `awk 'BEGIN{n=0} /"version":/ && n<2 {...; n++}'`; 6 transitive 4.0.0 deps left untouched
- [x] **Edge: no helper script** - manifest set is an inline Make variable + a bash `for` loop in the recipe, no external script
  - log: 2026-06-17 per the inline-metadata convention
