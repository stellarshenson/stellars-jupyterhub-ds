# Acceptance Criteria - Advanced menu ordering

The items in the Administration -> Advanced submenu are ordered alphabetically by label, so the menu stays predictable as leaves are added. Definition: `app/nav.ts` `NAV_ADMIN` Advanced `children`. Verified against the code 2026-06-18.

- [x] **Alphabetical by label** - Advanced children are listed A->Z by their `label`: Roles, Settings, Tokens
  - log: 2026-06-18 operator: "Advanced menu items must be ordered alphabetically"; reordered `children` in `nav.ts` (was Settings, Tokens, Roles)
- [x] **Case-insensitive, label-based** - ordering keys off the visible label, not the `id` or `path`
  - log: 2026-06-18 labels are Title Case; A->Z on the displayed text
- [x] **New leaves keep the order** - any item added to Advanced is inserted at its alphabetical position, not appended
  - log: 2026-06-18 comment in `nav.ts` records the rule for future additions
- [x] **Scope: Advanced only** - the rule applies to the Advanced submenu; top-level Administration items keep their deliberate workflow order (Servers, Users, Groups, Lab Setup, Events, Notifications, Advanced)
  - log: 2026-06-18 not alphabetised by design - top-level order is task-flow, not alphabetical
