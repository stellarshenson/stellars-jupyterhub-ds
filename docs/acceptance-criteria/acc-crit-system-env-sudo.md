# Acceptance Criteria - System Environment + Sudo Gate

New lab control `JUPYTERLAB_USER_ENV_ENABLE` (default on) governs whether a user may change SYSTEM-level env vars; off = their own shell env only. Sudo grants root (which can change system env anyway), so sudo is gated on it: system-env off forces sudo off, and sudo can never be on while system-env is off. Configurable as a platform default and per group, mirroring how sudo already works. Related: [[acc-crit-user-env-vars]], [[acc-crit-duoptimumhub]].

## Setting

- [ ] **Var** - hub injects `JUPYTERLAB_USER_ENV_ENABLE` (`1`/`0`) into every spawned lab, mirroring `JUPYTERLAB_SUDO_ENABLE`
  - log: 2026-07-08 added
- [ ] **Default on** - `1` unless a group or operator override says otherwise
  - log: 2026-07-08 added
- [ ] **Lab default** - `JUPYTERHUB_LAB_USER_ENV_ENABLE` on the Settings page (default `"1"`), loaded as `Settings.lab_user_env_enable`
  - log: 2026-07-08 added
- [ ] **Reserved** - `JUPYTERLAB_USER_ENV_ENABLE` added to `protected_env_dictionary.yml` so a user cannot set it themselves
  - log: 2026-07-08 added

## Sudo gate

- [ ] **Invariant** - effective sudo = `AND(sudo, system_env)`; system-env off forces sudo off
  - log: 2026-07-08 added
- [ ] **Enforced at spawn** - the gate is applied at spawn injection, so it holds even for a bad saved config; `JUPYTERLAB_SUDO_ENABLE=0` injected whenever system-env is off
  - log: 2026-07-08 added
- [ ] **Save rejected** - saving a group with sudo on + system-env off is rejected (or auto-corrected to sudo off)
  - log: 2026-07-08 added

## Group System section

- [ ] **Rename** - group policy "Sudo Access" section becomes "System" and holds both the system-env toggle and the sudo toggle; sudo behaviour unchanged
  - log: 2026-07-08 added
- [ ] **Live gate** - toggling system-env off in the form disables and forces off the sudo toggle (with a hint, not a silently inert switch); toggling it back on restores sudo to its prior value
  - log: 2026-07-08 added
- [ ] **Resolution** - system-env resolves priority-wins across a user's groups (highest-priority active group, else lab default), like sudo; the gate uses the resolved winner
  - log: 2026-07-08 added

## Edge cases

- [ ] **Edge: lab off, group on** - a group with system-env on gives its members system-env on; sudo then free
  - log: 2026-07-08 added
- [ ] **Edge: lab on, group off** - that group's members get system-env off and sudo capped off
  - log: 2026-07-08 added
- [ ] **Edge: no groups** - system-env on, sudo per `lab_sudo_enable`
  - log: 2026-07-08 added

## Per-user env editor (role gate)

- [ ] **User locked out** - when resolved system-env is off, the user cannot see or edit their own per-user env vars; the editor is hidden for them (platform role-level restriction)
  - log: 2026-07-08 added
- [ ] **Admin retains** - an admin can always view and edit any user's per-user env vars, regardless of that user's system-env state
  - log: 2026-07-08 added
- [ ] **Not injected** - when system-env is off, the user's stored per-user env vars are not injected at spawn; retained and re-applied if system-env is re-enabled
  - log: 2026-07-08 added

## Verification

- [ ] **Unit** - settings-loader cross-check; resolution + gate tests; coerce rejects sudo-on+env-off; protected-name includes the var; spawn-injection asserts both vars and the gate
  - log: 2026-07-08 added
- [ ] **Functional** (acc_crit-marked, rebuilt image) - spawn asserts `JUPYTERLAB_USER_ENV_ENABLE` present; a group with system-env off yields `JUPYTERLAB_SUDO_ENABLE=0` even with sudo set on
  - log: 2026-07-08 added
- [ ] **Adversarial** - survives `/adversarial-review` security, architect and ux lenses; re-confirm clean after fixes
  - log: 2026-07-08 added
