# Acceptance Criteria - Volume reset confirmation

After an admin/user resets selected volumes, the panel reports what was done and offers a clean way back. The list paints volume names instantly with sizes filling in (see [acc-crit-resource-bars] for the names/sizes split). `optimum-hub-web/src/components/VolumeReset.tsx`, `pages/ManageVolumes.tsx`.

## After reset (same screen, no separate view)

- [x] **Stays on the volumes screen** - resetting does NOT switch to a separate confirmation view; the same table + buttons remain and the removed rows are marked in place
  - log: 2026-06-17 reworked (operator: "stay on the same one with the same buttons") - dropped the `done` early-return; `removed` suffixes marked in the table
- [x] **"removed" in red, not a pill** - each removed volume reads "removed" in dangerous (red) text in its Size cell, never an antd Tag/pill
  - log: 2026-06-17 `oh-text-danger` in the Size column; cross-ref [acc-crit-design-language] text colours
- [x] **Removed rows non-selectable** - a removed volume's checkbox is disabled so it cannot be re-selected; Reset re-disables when nothing is selected
  - log: 2026-06-17 `getCheckboxProps` disabled on removed suffixes
- [x] **Irreversibility warning** - the top notice is a WARNING (not the info/activity "EKG" glyph) stating that removing volumes is irreversible - the selected volumes and all their contents are permanently deleted
  - log: 2026-06-17 reworked (operator: "warning that selecting and removing the volumes is irreversible; not the current EKG message") - Notice type warning, was info

## Close behaviour

- [x] **Cancel + Done footer** - the dedicated Manage-volumes page uses the standard config footer (Reset destructive on the left; Cancel + a primary Done on the right), matching Configure-user / Configure-group; both Cancel and Done leave the screen
  - log: 2026-06-17 implemented - `VolumeReset` renders `FormFooter` in page mode (when `onClose` is set); the Configure-user Volumes TAB keeps the bare Reset button (UserConfig owns that footer)
- [x] **Returns to the true origin** - Cancel / Done return to where the screen was opened from per the nav-origin state - Home if opened from Home, Servers if opened from the Servers list - not a hardcoded /servers
  - log: 2026-06-17 implemented - `ManageVolumes` reads `location.state.from` (`backTo`); Home hero / widget + Servers list all tag the origin; was the reported bug (Home -> volumes closed to Servers); cross-ref [acc-crit-design-language] "Respect the navigation path"
- [x] **Edge: reached from the user-config Volumes tab vs the dedicated Manage-volumes page** - Close returns to whichever parent opened it (the tab keeps its own footer; the page returns to its origin), not a dead-end empty panel
  - log: 2026-06-17 implemented - page mode renders the footer; tab mode (no `onClose`) renders just the Reset action

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
