# Acceptance Criteria - System Environment + Sudo Gate

New lab control `JUPYTERLAB_USER_ENV_ENABLE` (default on) governs whether a user may change SYSTEM-level env vars; off = their own shell env only. Sudo grants root (which can change system env anyway), so sudo is gated on it: system-env off forces sudo off, and sudo can never be on while system-env is off. Configurable as a platform default and per group, mirroring how sudo already works. Related: [[acc-crit-user-env-vars]], [[acc-crit-duoptimumhub]].

## Setting

- [x] **Var** - hub injects `JUPYTERLAB_USER_ENV_ENABLE` (`1`/`0`) into every spawned lab, mirroring `JUPYTERLAB_SUDO_ENABLE`
  - log: 2026-07-08 added
  - log: 2026-07-09 verified on a real container (functional gate)
- [x] **Default on** - `1` unless a group or operator override says otherwise
  - log: 2026-07-08 added
  - log: 2026-07-09 verified (loader default + settings-loader cross-check)
- [x] **Lab default** - `JUPYTERHUB_LAB_USER_ENV_ENABLE` on the Settings page (default `"1"`), loaded as `Settings.lab_user_env_enable`
  - log: 2026-07-08 added
  - log: 2026-07-09 verified - loader import + `stellars_config`/pre-spawn export architect-reviewed CLEAN (mirrors `JUPYTERHUB_LAB_SUDO_ENABLE` byte-for-byte, no drift)
- [x] **Lab default exported** - the var is surfaced on the read-only settings API (`GET /hub/api/settings`) with its live value, the source the admin Settings page renders
  - log: 2026-07-09 added; functional test `test_lab_user_env_default_in_settings_api` asserts it alongside its sudo sibling
  - log: 2026-07-09 verified MET on the rebuilt image (v4.0.21, id 474ba94) - full gate 225/225
- [x] **Reserved** - `JUPYTERLAB_USER_ENV_ENABLE` added to `protected_env_dictionary.yml` (and the `DEFAULT_PROTECTED_NAMES` code fallback) so a user cannot set it themselves
  - log: 2026-07-08 added
  - log: 2026-07-09 verified - dictionary/fallback parity confirmed by the architect sweep

## Sudo gate

- [x] **Invariant** - effective sudo = `AND(sudo, system_env)`; system-env off forces sudo off
  - log: 2026-07-08 added
  - log: 2026-07-09 verified (unit gate tests + functional container assertion)
- [x] **Enforced at spawn** - the gate is applied at spawn injection, so it holds even for a bad saved config; `JUPYTERLAB_SUDO_ENABLE=0` injected whenever system-env is off
  - log: 2026-07-08 added
  - log: 2026-07-09 verified on a real container (functional gate)
- [x] **Save rejected** - saving a group with sudo on + system-env off is rejected (or auto-corrected to sudo off)
  - log: 2026-07-08 added
  - log: 2026-07-09 verified (validate() unit tests + client pre-gate)

## Group System section

- [x] **Rename** - group policy "Sudo Access" section becomes "System Access" and holds both the system-env toggle and the sudo toggle; sudo behaviour unchanged
  - log: 2026-07-08 added
  - log: 2026-07-09 verified end-to-end (prior functional gate + tri-lens review)
- [x] **Live gate** - toggling system-env off in the form disables the sudo toggle AND zeroes sudo, and shows a standardised warning `Notice` below the rows explaining sudo needs system env; re-enabling system-env leaves sudo OFF (no silent resurrection of a root grant - the admin re-enables it deliberately)
  - log: 2026-07-08 added
  - log: 2026-07-09 restyled - de-nested the two switches into evenly-spaced sibling rows; inline hint replaced by the design-system `Notice` (was a cramped label hint, then an antd Alert); gate logic unchanged
- [x] **Resolution** - system-env resolves priority-wins across a user's groups (highest-priority active group, else lab default), like sudo; the gate uses the resolved winner
  - log: 2026-07-08 added
  - log: 2026-07-09 verified (golden resolution + tri-lens architect NO VIOLATIONS)

## Edge cases

- [x] **Edge: lab off, group on** - a group with system-env on gives its members system-env on; sudo then free
  - log: 2026-07-08 added
  - log: 2026-07-09 verified (resolution golden + gate unit tests)
- [x] **Edge: lab on, group off** - that group's members get system-env off and sudo capped off
  - log: 2026-07-08 added
  - log: 2026-07-09 verified on a real container (functional gate)
- [x] **Edge: no groups** - system-env on, sudo per `lab_sudo_enable`
  - log: 2026-07-08 added
  - log: 2026-07-09 verified (effective_user_env_enable falls back to lab default)

## Per-user env editor (role gate)

- [x] **User locked out** - when resolved system-env is off, the user cannot see or edit their own per-user env vars; the editor is hidden for them (platform role-level restriction)
  - log: 2026-07-08 added
  - log: 2026-07-09 verified (handler GET withholds + PUT 403 unit tests; Profile shows the locked Alert)
- [x] **Admin retains** - an admin can always view and edit any user's per-user env vars, regardless of that user's system-env state
  - log: 2026-07-08 added
  - log: 2026-07-09 verified (role-gate unit tests)
- [x] **Not injected** - when system-env is off, the user's stored per-user env vars are not injected at spawn; retained and re-applied if system-env is re-enabled
  - log: 2026-07-08 added
  - log: 2026-07-09 verified (tracked-key spawn-hook unit tests)

## Verification

- [x] **Unit** - settings-loader cross-check; resolution + gate tests; coerce rejects sudo-on+env-off; protected-name includes the var; spawn-injection asserts both vars and the gate
  - log: 2026-07-08 added
  - log: 2026-07-09 verified - backend suite green (prior session)
- [x] **Functional** (acc_crit-marked, rebuilt image) - spawn asserts `JUPYTERLAB_USER_ENV_ENABLE` present; a group with system-env off yields `JUPYTERLAB_SUDO_ENABLE=0` even with sudo set on
  - log: 2026-07-08 added
  - log: 2026-07-09 verified - full gate 225/225 on rebuilt v4.0.21 image; added `test_lab_user_env_default_in_settings_api` for the settings-export surface (MET)
- [x] **Adversarial** - survives `/adversarial-review` security, architect and ux lenses; re-confirm clean after fixes
  - log: 2026-07-08 added
  - log: 2026-07-09 - settings import/export architect sweep returned CLEAN (loader import + dictionary/stellars_config/pre-spawn export mirror the sudo sibling, no drift)
