# Acceptance Criteria - docker policy access mode

The group-policy Docker section's enable toggle means "docker access granted". There is no separate "No docker access" choice (that is the toggle being off). When enabled, the only choice is HOW access is granted: Standard (raw socket) or Limited (per-user filtered proxy, the default), with Privileged orthogonal.

- [x] **No "none" option** - the radio offers only Standard and Limited; the redundant "No Docker access" entry is removed
  - log: 2026-06-17 `GroupPolicyTab.tsx` docker section
- [x] **Toggle grants** - `docker_active` (the section switch) being on = access granted; off = no docker, and both `docker_access`/`docker_limited` emit false
  - log: 2026-06-17 emission gated on `(on.docker ?? false)`
- [x] **Limited is the default** - when the section is enabled and Standard is not chosen, the mode is Limited; the quota panel shows for Limited
  - log: 2026-06-17 `dStd` is the only stored flag; limited = `!dStd`; quota panel gated on `!dStd`
- [x] **Emission coherence** - on -> exactly one of `docker_access`(std) / `docker_limited`(limited) is true; off -> both false; `docker_privileged` independent
  - log: 2026-06-17 `docker_access: on && dStd`, `docker_limited: on && !dStd`
- [x] **Legacy config migrates** - a stored config that was "active but neither mode" (the old none-while-on state) reads as Limited (the default), not a broken empty mode
  - log: 2026-06-17 init sets `dStd` from `docker_access`; not-standard reads as limited
- [x] **Privileged orthogonal** - the Privileged checkbox is independent of the access mode and unaffected by this change
  - log: 2026-06-17 `dPriv` unchanged
- [ ] **Runtime: edit + save round-trips** - on the live hub, a group with docker enabled saves as limited (or standard) and re-opens to the same mode
  - log: 2026-06-17 frontend + build clean; on-screen confirm pends operator rebuild
