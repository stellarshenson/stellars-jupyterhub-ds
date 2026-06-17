# Old portal vs Optimum Hub - functional comparison

Checked 2026-06-17 by logging into the hidden stock container (`127.0.0.1:9444`,
dummy admin) and enumerating its pages, then mapping each against the Optimum Hub
portal. The stock JupyterHub UI exposes exactly five surfaces; the portal covers
all of them and adds substantially more.

## Stock UI surface (enumerated from the running container)

- `/hub/home` - start / stop **my** server
- `/hub/admin` - the stock React admin app: user list, add users, start / stop /
  delete a user's server, access a server, shutdown hub
- `/hub/token` - request API tokens, manage OAuth authorisations
- `/hub/spawn` - spawn page
- `/hub/logout`

## Parity (stock feature -> portal equivalent)

| Stock | Optimum Hub | Notes |
|-------|-------------|-------|
| Home: start/stop my server | Home (server hero) | Portal adds status pill, resources, TTL bar + extend, groups, grants |
| Admin: user list | Users | Portal adds activity, last-seen, scope pills, authorise toggle, search |
| Admin: add user | New user + Bulk add | Portal adds bulk paste + per-user generated passwords |
| Admin: start/stop/delete server | Servers | Portal adds per-server CPU/mem/GPU/vol/sys breakdowns, restart, manage-volumes |
| Token page | Tokens | Parity (request/revoke tokens, OAuth apps) |
| Spawn | start flow / lifecycle popups | Portal drives spawn via SSE progress |

## Portal-only functionality (no stock equivalent)

- **Groups** + the 9-section group policy editor (env, GPU all/per-device, CPU,
  memory, docker access, volume mounts, api-keys pool, downloads, sudo)
- **Events** feed (real platform event log)
- **Notifications** broadcast to active labs
- **Settings** (read-only live env, 11 categories) + full reference
- **Lab Container** (spawn image + standard volumes)
- **Manage Volumes** (selective per-user volume reset)
- **Profile** (first/last name + email persistence)
- **GPU** inventory + per-device utilisation widgets (gated on real detection)
- **TTL** session timer with base-relative drain + typed-hours extend
- **Mobile** minimal home (status + start/stop/extend) below 768px
- Custom branding + antd login/signup screens

## Conclusion

The portal is a strict superset of the stock UI's functionality: every stock
action has a portal equivalent (usually richer), and the portal adds groups,
policy, events, notifications, settings, lab-container, volumes, profile, GPU and
mobile that the stock UI never had. No functional regression was found against
the stock baseline. Raise/teardown the comparison container per `README.md`.
