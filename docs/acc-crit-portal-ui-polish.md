# Acceptance Criteria - Portal UI Polish (2026-06-17 session)

Running checklist for the rapid UI feedback pass: TTL animation, GPU labels + rich tooltip, list tooltips, resource tooltips, upgrade pill, footer, list sub-names. Status is honest - `[x]` = in code + verified (tests/typecheck), `[ ]` = pending; backend-dependent items are flagged. Nothing here is live until the next image rebuild.

## TTL extend

- [x] **Extend refetches the bar** - `extendSession` invalidates `['hero', user]` so the bar refetches; backend persists `cull_at` and `remaining_seconds_for` reads it
  - log: 2026-06-17 fixed + verified (backend round-trip read end-to-end, invalidate confirmed); a "still 50%" rebuild predates this fix
- [ ] **Animate the increase** - on extend the bar should animate up to the new remaining, not snap
  - log: 2026-06-17 antd `Progress` transitions on percent change by default - expected free once the refetch lands; confirm visually after rebuild

## GPU labels + tooltip

- [x] **Mini name as bar label** - per-GPU bar labels show the stripped name ("5090") not the index
  - log: 2026-06-17 implemented (shortGpuName + GpuMeter)
- [ ] **Full name fits before the bar (single line)** - the device-name label column is wide enough for the full short name ("A500 Embedded GPU"), single line, never wrapped/truncated, bar flexes after it
  - log: 2026-06-17 pending - needs `.oh-gpurow` layout: name `white-space:nowrap` + natural width, bar `flex:1`
- [ ] **Rich multiline GPU tooltip** - hover shows full info, one field per line, like the old design: full name, UUID, memory total, current utilisation, memory used, temperature, wattage
  - log: 2026-06-17 pending; PARTIAL data only - name/uuid/mem-total/utilisation/mem-used are available (uuid in inventory, dropped by gpu_cache so must be threaded); **temperature + wattage are NOT queried by the sidecar** (`_GPU_QUERY`), so they need: sidecar `_GPU_QUERY += temperature.gpu,power.draw` + schema + image rebuild, then gpu_cache + activity entry + GpuDevice type + tooltip
  - [ ] **Sub: extend sidecar** - add `temperature.gpu`, `power.draw` to `_GPU_QUERY` + schema (`gpuinfo-nvidia`, separate image)
  - [ ] **Sub: thread fields** - keep uuid/temp/power through `gpu_cache` -> activity gpu entry -> `GpuDevice` -> tooltip

## List + resource tooltips

- [ ] **Multiline list tooltips** - long tooltips on Servers, Users and Groups lists wrap to a sensible max-width multiline box, not one ridiculously long line
  - log: 2026-06-17 pending (tooltip `overlayStyle` max-width + normal white-space); names/labels themselves stay single-line (multiline name breaks the row visuals)
- [ ] **Resource widget tooltips** - on the server resources widget both the % value and the progress bar carry a detail tooltip (not just the bar)
  - log: 2026-06-17 pending (ResourceBars: tooltip on the value span + the bar)

## Upgrade pill

- [x] **Desktop pill** - gold "Upgrade available" left of the status pill on the Server status card, running servers only
  - log: 2026-06-17 implemented + running-gated
- [x] **Mobile pill** - same pill on the mobile MyServerCard header, running only
  - log: 2026-06-17 implemented (MobileHome), typecheck clean
- [x] **Recency check** - `docker image ls` newest local image for the repo vs the running container's image created time (`image_upgrade_available`, 6 unit tests); unknown -> no pill
  - log: 2026-06-17 implemented + tested

## Misc

- [x] **Footer label** - bottom stack chip reads "Ant Design" not "Ant Design Pro"
  - log: 2026-06-17 done (AppLayout VersionFooter)
- [ ] **First/last name in users list** - the users list shows the profile first/last name as a sub-name under the username
  - log: 2026-06-17 pending (#186) - `getUsers` does not surface profile first/last; also depends on the profile save actually persisting (#183 "Failed to fetch"); user reports the saved name does not appear -> both needed

## Verification

- [x] **Backend + frontend green** - `make test` 564, docker-proxy 63, portal `tsc --noEmit` clean as of this session
  - log: 2026-06-17
- [ ] **Live** - rebuild + hard refresh; confirm TTL animates up on extend, GPU names fit, tooltips wrap, pill shows
  - log: 2026-06-17 pending user rebuild
