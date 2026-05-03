# Changelog

All notable changes to `stellars-jupyterhub-ds` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses semantic versioning suffixed with the underlying CUDA / JupyterHub upstream image versions in git tags (e.g. `3.10.9_cuda-13.0.2_jh-5.4.2`).

## [3.10.9] - 2026-05-03

### Added
- `make preflight` command verifies all required tools, services, and project files are in place before any build or deployment action. Runs automatically before every build / push / start / stop command.
- Colour-coded status banners during builds and pushes: cyan for version-bump messages, green for build / push success, red for preflight failures.

### Changed
- Renamed Make targets so the names match behaviour: `make rebuild` is the safe default that does not bump versions; `make rebuild_increment_version` is the bump-and-build path. The previous names were the other way around.

### Fixed
- `make rebuild && make push` was producing corrupted version strings with spaces, which then broke the docker tag. Version bumper now produces clean dot-joined output.
- Spurious "secret in environment" warning during docker builds, triggered by environment variables whose names contain "PASSWORD" but actually configure password-generation parameters, not credentials.

### Removed
- Stray `uv.lock` from the repository root - never needed (the root `pyproject.toml` is a metadata-only descriptor with no dependencies). Future accidental re-creation is now blocked via `.gitignore`.

## [3.10.8] - 2026-05-03

### Added
- **Operator config overlay**: drop your own `jupyterhub_config.py` (and any helper modules) into a `config/` folder next to `compose.yml` to override the default behaviour. Missing or empty folder uses the built-in defaults; an empty file or syntax-broken config fails boot loudly so typos surface immediately rather than silently masking. New `docs/configuration.md` walks through the layout and override patterns.

### Changed
- `compose.yml` is now a fully standalone artefact - operators do not need any extra files on disk to run the platform. The image ships a working built-in config; operator overlays are picked up automatically when present.
- Project metadata moved from `project.env` to a standard `pyproject.toml`. Quickstart and Customisation sections of the README updated to match.

### Removed
- The hard-coded host config bind-mount in `compose.yml`. Use the new `./config/` overlay pattern instead.

## [3.10.7] - 2026-05-02

### Added
- **Operator TLS cert overlay**: drop your TLS yml + cert / key files into a `certs/` folder next to `compose.yml` to use your own certificates; missing or empty folder auto-generates a self-signed cert. Status banner on every boot logs which certs are active and their expiry. New `docs/certificates.md` walks through the layout.
- New `JUPYTERHUB_USER_VOLUMES_DESCRIPTIONS_FILE` env: optional overlay YAML to override or extend per-volume descriptions and mount points without rebuilding the image. Documented in `docs/user-volumes.md`.
- `Manage Volumes` UI now lists only volumes that actually exist for the user, with a friendly empty-state message for users who have not spawned a server yet.

### Changed
- Volume names shown in `Manage Volumes` modals now match what is on disk, including for usernames with special characters like dots.
- Confirmation banner colour in `Manage Volumes` modals changed from red (alarming) to yellow (warning) - resetting volumes is a heads-up, not a destructive action.

### Fixed
- `Manage Volumes` resets were silently no-op for users with the new namespaced volume names introduced in 3.10.5. Fixed.

## [3.10.6] - 2026-04-30

### Added
- **Chip-input "Add Users to Group" editor**: bulk-add or remove many users at once on the group editor page using an Outlook / Gmail-style chip + autocomplete control. Confirmation modal lists who was added or removed on Apply.

### Changed
- `JUPYTERHUB_NETWORK_NAME` is now visible inside spawned JupyterLab containers.
- Polished the companion deployment template (`copier-stellars-jupyterhub-ds`): clearer questions, fewer questions, MIT licence.

### Fixed
- Container build was silently skipping packages from the manifest because of a broken upstream package source. Build now fails loudly if anything goes wrong.

## [3.10.5] - 2026-04-30

### Added
- **Copier deployment template**: companion repo `copier-stellars-jupyterhub-ds` (tagged v1.0.2). Generates a thin overlay directory via a short interview; deployments stay upgradeable - pull new upstream commits without touching the generated overlay.

### Changed
- `COMPOSE_PROJECT_NAME` now drives volume / network / container namespacing as the single source of truth. User containers appear under a Docker Compose project in `docker compose ls`.

### Fixed
- First-time admin signup now completes without email or SMTP. Bootstrap also re-evaluates dynamically, so the admin can create new users via the admin panel immediately after their own signup.

## [3.10.2] - 2026-04-23

### Added
- **Groups admin page** (`/hub/groups`): create, delete, and configure user groups. Per-group settings include custom environment variables, GPU access, Docker engine access, privileged mode, and per-user memory limit (GB). Drag-and-drop sets priority. Reserved environment variable names rejected with inline error.
- Per-group memory limit wired through to user containers.
- Post-Apply confirmation modal on the stock admin panel listing added (green) and removed (red) users per affected group.
- `JUPYTERLAB_SYSTEM_NAME` passthrough to user containers - drives welcome page, MOTD, and JupyterLab toolbar header. Optional `JUPYTERLAB_HEADER_CAPITALIZE_SYSTEM_NAME` and `JUPYTERLAB_HEADER_SYSTEM_NAME_COLOR` for fine-grained branding.

### Changed
- User access (Docker, GPU, privileged, env vars, memory limit) is now resolved at spawn time by combining all of the user's groups: grants OR-accumulate, env vars use highest-priority wins on conflict, memory limit uses biggest value wins.

### Fixed
- Confirmation modal was missing in some cases when group membership was edited then partially undone before Apply. Fixed.

## [3.10.0] - 2026-04-30

### Added
- **First version of the Groups admin page** at `/hub/groups`: per-group configuration (env vars, GPU, Docker access) persisted to disk.

### Removed
- Auto-creation of `docker-sock` / `docker-privileged` groups at startup. Operators must explicitly create access groups via the new Groups page.

### Fixed
- Empty Groups list on fresh deployments. Add Group button now appears even when no groups exist.

---

For 3.9.x, 3.8.x, and earlier patch history see `.claude/JOURNAL.md` and `git log --tags --decorate`.
