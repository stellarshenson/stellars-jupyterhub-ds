# Acceptance Criteria - Platform event log (persistence + clear)

The portal's audit feed (Overview "Recent events" + the Events page) is backed by a persistent SQLite store, so events survive a hub restart; an admin can clear the whole log from the Events panel. Store: `optimum_hub_services/event_log.py` (`/data/event_log.sqlite`); handler: `handlers/events_data.py`; UI: `pages/Events.tsx`.

## Persistence

- [x] **Stored in SQLite, not memory** - events are written to `/data/event_log.sqlite` (the persistent `jupyterhub_data` volume), so they survive a hub restart / recreate
  - log: 2026-06-18 verified - `EventLogManager` SQLAlchemy store (was the operator's question "are events saved anywhere?")
- [x] **Bounded** - the table is pruned to the most recent 1000 rows on each record, so it never grows unbounded
  - log: 2026-06-18 `_MAX_ROWS = 1000`, prune-on-record
- [x] **Override path** - `STELLARS_EVENT_LOG_DB_PATH` overrides the DB location (tests point it at a temp file)
  - log: 2026-06-18 env override

## Clear action

- [x] **Clear button in the Events panel** - the Events toolbar has a danger-toned "Clear log" button (close icon), disabled when the feed is already empty
  - log: 2026-06-18 `Events.tsx` toolBarRender; operator "clear them - using action in the events panel - design that action button"
- [x] **Confirm before clearing** - clicking it opens a confirm modal ("Clear the event log? This permanently deletes every recorded event. This cannot be undone.") with a danger OK
  - log: 2026-06-18 `Modal.confirm` + danger okButtonProps
- [x] **Wipes the store** - confirming calls `DELETE /hub/api/events` -> `EventLogManager.clear()` (admin-only), emptying the table; the feed refetches empty
  - log: 2026-06-18 `clearEvents` op invalidates `['events']`; handler `delete` guarded on `current_user.admin`
- [x] **Admin-only** - both GET and DELETE on `/api/events` 403 for non-admins
  - log: 2026-06-18 `@web.authenticated` + admin check on both methods
- [x] **Log keeps working after a clear** - new events record normally into the emptied store
  - log: 2026-06-18 covered by `test_clear_empties_the_log`
- [ ] **Edge: clear is not itself audited** - clearing leaves the log empty (no "log cleared" marker is recorded); revisit if an audit trail of the clear is wanted
  - log: 2026-06-18 by design - literal "clear"; flag for the operator

## API

- `GET /hub/api/events` -> `{events: [{id, ts, type, text}]}` (admin, newest first, <=100)
- `DELETE /hub/api/events` -> `{cleared: <n>}` (admin) - empties the log

## Tests

- [x] **Store unit tests** - record/recent/prune/clear covered in `tests/test_event_log.py`
  - log: 2026-06-18 added `test_clear_empties_the_log` + `test_clear_empty_log_is_noop` (6 passing)
