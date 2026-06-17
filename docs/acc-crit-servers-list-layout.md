# Acceptance Criteria - Servers list layout

The Servers page table column structure, ordering, alignment, widths, and the user-name + time-left columns. Distinct from the Server widget (which intentionally clubs status + last-activity); the LIST keeps them as separate columns. `optimum-hub-web/src/pages/Servers.tsx`.

## Columns and order

- [ ] **Status and Last activity are separate columns** - the list does NOT club last-activity into the status label (unlike the widget); Status is its own column, Last activity its own
  - log: 2026-06-17 criterion added (#248)
- [ ] **Column order** - Status, then Last activity, then Activity tracker (left to right)
  - log: 2026-06-17 criterion added (#248)
- [ ] **Status column just wide enough** - the Status column is sized to its content, not over-wide
  - log: 2026-06-17 criterion added (#250)
- [ ] **Last activity column just wide enough** - same: sized to content, not over-wide
  - log: 2026-06-17 criterion added (#250)

## Activity column

- [ ] **Activity meter centered** - the activity tracker is centered within its column, not left-aligned
  - log: 2026-06-17 criterion added (#248)
- [ ] **Activity tooltip: real uncapped %** - the tooltip shows the REAL activity % which MAY exceed 100% (>100% is desirable - the user works more than the 8h/day target); not clamped
  - log: 2026-06-17 criterion added (#247); cross-ref [acc-crit-activity-scoring]
- [ ] **Activity tooltip multiline** - the % plus the existing info (avg active hours/day) on separate lines, not one super-long single line
  - log: 2026-06-17 criterion added (#247)

## User name column

- [ ] **Name is a link to the user** - the username links to the user config page (same target as the Users page), no artificial click-friction
  - log: 2026-06-17 criterion added (#249)
- [ ] **First + last name shown** - the cell shows the user's first and last name exactly like the Users page (name under / alongside the username), from the same profile source
  - log: 2026-06-17 criterion added (#249)

## Time-left column

- [ ] **Tooltip: hours over standard TTL** - the Time-left tooltip states how many hours over the standard (base) TTL the session currently is (the extension beyond the base timeout)
  - log: 2026-06-17 criterion added (#251)
- [ ] **Edge: not extended** - when the session is at or under the base TTL, the tooltip does not claim a negative over-hours (shows none / "within standard TTL")
  - log: 2026-06-17 criterion added (#251)

## Reflected in the design language

- [ ] **Visual cues on /design-language** - the column-separation, ordering, alignment, and name-as-link conventions are shown on the design-language page as visual cues (not before/after examples)
  - log: 2026-06-17 criterion added (#252); cross-ref [acc-crit-design-language]
