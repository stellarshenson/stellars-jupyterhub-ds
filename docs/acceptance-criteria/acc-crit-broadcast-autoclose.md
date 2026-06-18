# Acceptance Criteria - broadcast auto-close duration

The notifications broadcast composer picks an auto-close duration from five presets instead of an on/off toggle. The chosen value (milliseconds) flows to the lab Notification API via the broadcast payload.

- [x] **Five presets** - 30s, 1min, 10min, 30min, 1h, rendered as a segmented control
  - log: 2026-06-17 `AUTO_CLOSE_OPTIONS` (ms values) + antd `Segmented`; `pages/Notifications.tsx`
- [x] **Default 30s** - 30s is auto-selected on load
  - log: 2026-06-17 `useState(30000)`
- [x] **User-changeable** - the admin picks any preset before sending
  - log: 2026-06-17 `onChange={setAutoCloseMs}`
- [x] **Wired through** - `broadcast(message, variant, autoCloseMs, recipients)` sends `autoClose` (ms) in the POST body; the backend forwards it to the notification payload unchanged
  - log: 2026-06-17 `ops.broadcast` type `number | boolean`; backend `BroadcastNotificationHandler` passes `autoClose` through
- [x] **Correct unit** - values are milliseconds, what JupyterLab's `Notification` autoClose expects
  - log: 2026-06-17 30000 / 60000 / 600000 / 1800000 / 3600000

## API

- `POST /hub/api/notifications/broadcast` body `autoClose: number` (ms) - forwarded to each lab's notification ingest as `autoClose`
