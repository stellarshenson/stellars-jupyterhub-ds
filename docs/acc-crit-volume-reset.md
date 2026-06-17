# Acceptance Criteria - Volume reset confirmation

After an admin/user resets selected volumes, the panel reports what was done and offers a clean way back. The list paints volume names instantly with sizes filling in (see [acc-crit-resource-bars] for the names/sizes split). `optimum-hub-web/src/components/VolumeReset.tsx`, `pages/ManageVolumes.tsx`.

## Done report

- [ ] **Quick confirmation line** - a short success message states the reset happened (e.g. "Reset N volume(s) for <user>")
  - log: 2026-06-17 criterion added (#244); current message is malformed - to fix
- [ ] **Volume list in normal text** - below the confirmation, the affected volumes are listed in normal body text (one per line / readable), not crammed into the confirmation line
  - log: 2026-06-17 criterion added (#244)
- [ ] **Removed pill per volume** - each listed volume carries a pill/tag stating it was removed
  - log: 2026-06-17 criterion added (#244)

## Close behaviour

- [ ] **Close returns to the parent screen** - clicking Close navigates back to the screen the user came from (the parent), NOT the now-empty remove-volumes screen
  - log: 2026-06-17 criterion added (#244); current bug - Close lands on the empty volumes screen
- [ ] **Edge: reached from the user-config Volumes tab vs the dedicated Manage-volumes page** - Close returns to whichever parent opened it (the tab stays, or the page returns to /servers), not a dead-end empty panel
  - log: 2026-06-17 criterion added (#244)

## Audit

- [x] **Event logged on reset** - a successful reset records a `volume` event on the event log (`record_event`), surfaced in Recent events and on the Events page with the disk icon and a `warn` tone; hub log keeps its `[Manage Volumes]` lines too
  - log: 2026-06-17 added; `handlers/volumes.py` after the removal loop, only when >=1 volume actually removed
- [x] **Event names actor and owner** - text names the actor; when an admin resets another user's volumes it names both ("<b>admin</b> reset <b>alice</b> volumes: home, workspace"), all HTML-escaped
  - log: 2026-06-17 added
- [x] **No UI notify** - the event log + hub log are the record; no extra toast/notification is sent on reset
  - log: 2026-06-17 per request - event log only
- [ ] **Edge: all requested volumes already gone** - when nothing is actually removed (all not-found) no event is recorded
  - log: 2026-06-17 added; guarded on non-empty `reset_volumes`

## Already in place (keep)

- [x] **Names instant, sizes fill in** - the table paints volume names at once and sizes show "updating…" then fill (split fast names / slow sizes)
  - log: 2026-06-17 shipped (#242)
- [x] **Reset gated on stopped server** - reset is disabled while the server runs (backend also rejects)
  - log: 2026-06-17 pre-existing
