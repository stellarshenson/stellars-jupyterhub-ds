# Acceptance Criteria - "Upgrade available" pill

The home/server "Upgrade available" pill tells a user that a stop/start would land their lab on a newer image. Detection compares image IDs (not `Created` times): the running container's image is frequently pruned right after a rebuild - the very moment an upgrade exists - so its timestamp is unreadable; the reliable signal is that the configured lab image tag now resolves to a different id than the one the container runs. Backend `docker_utils.newer_lab_image_available` + pure `image_upgrade_available`; surfaced as `/activity` `lab_image_upgrade_available` -> `hero.upgradeAvailable`.

## Detection algorithm

- [x] **Ref from settings** - the compared ref is the configured lab image (`stellars_config['lab_image']` = `JUPYTERHUB_LAB_IMAGE`), passed per-container to `newer_lab_image_available(image_ref, container_image_id)`
  - log: 2026-06-17 verified (activity.py:164,176)
- [x] **No tag -> :latest** - a ref with no tag on its final path segment gets an implicit `:latest` (docker's own default); a `@sha256` digest is stripped (`_normalize_ref`)
  - log: 2026-06-17 implemented (`_normalize_ref`)
- [x] **Tag supplied -> use it** - a ref that already carries a tag (`repo:3.8.5`, `repo:latest`) is compared on that exact tag, not coerced
  - log: 2026-06-17 implemented (`_normalize_ref` leaves a tagged ref unchanged)
- [x] **Compare resolved-tag id vs running id** - `tag_to_id[ref]` (the id the tag currently points to) is compared to the running container's `container.attrs['Image']`; differ -> candidate upgrade
  - log: 2026-06-17 implemented; verified live (konrad running `0ee110` vs `:latest` `1c4b02` -> True)
- [x] **Guard: tag must be the repo's newest** - the candidate only fires when the resolved tag id equals the repo's newest-by-`Created` image id, so a deliberate re-tag of the lab tag to an OLDER image never offers a false upgrade
  - log: 2026-06-17 implemented (`image_upgrade_available(latest_tag_id, container_image_id, newest_repo_id)`)
- [x] **ID comparison, not Created** - the running image's `Created` is NOT read (it is gone from the store after a rebuild+prune); only ids are compared, with `Created` used solely to pick the repo's newest image
  - log: 2026-06-17 root-caused on the live host - `docker image inspect <running id>` returned "No such image"; the prior Created-vs-Created compare could never fire

## Created parsing (why the old code never fired)

- [x] **ISO-8601 string parse** - docker-py returns image `Created` as an ISO-8601 string with nanosecond precision + trailing `Z` (`2026-06-17T11:20:48.755861714Z`), not an epoch int; `_parse_created` normalises `Z`->`+00:00`, trims ns->us, and `datetime.fromisoformat`s it
  - log: 2026-06-17 FIXED - the old `if not isinstance(created, int): continue` skipped EVERY image, so `newest_by_repo` was always empty and the pill was dead for every user
- [x] **Epoch fallback** - an int/float `Created` (older docker clients) is accepted as-is
  - log: 2026-06-17 covered (`isinstance(created, (int, float))`)
- [x] **Unparseable -> None** - a malformed/empty `Created` yields None and the image is skipped for the newest-by-repo calc (never crashes the snapshot)
  - log: 2026-06-17 covered (try/except ValueError)

## Snapshot + caching

- [x] **One snapshot, dict lookups** - `docker image ls -a` is snapshotted to `(tag_to_id, newest_id_by_repo)` and cached `_IMAGE_TTL` = 300s so the polled `/activity` endpoint does a dict lookup, not a socket call per user
  - log: 2026-06-17 retained (cache shape changed from `(created_by_id, newest_by_repo)`)
- [x] **Dangling/untagged skipped** - tags whose repo is `<none>` are not indexed
  - log: 2026-06-17 verified (`repo == '<none>'` skip)

## Display

- [x] **Running server only** - the pill shows only for an active server (the upgrade check runs on the container stats path, default `lab_image_upgrade_available: False`)
  - log: 2026-06-17 verified (activity.py only sets it inside the active-users stats merge)
- [x] **Label is "Update available"** - the user-facing pill label reads "Update available" (capital U); internal identifiers (`upgradeAvailable`, `lab_image_upgrade_available`) keep "upgrade"
  - log: 2026-06-18 renamed (operator "upgrade available -> update available ... with capital U") in `ServerHero.tsx` + `MobileHome.tsx`; also the /design-language reference text
- [ ] **Pill desktop + mobile** - `hero.upgradeAvailable` renders a gold "Update available" pill on the "Server Control" card (desktop) and the mobile MyServerCard
  - log: 2026-06-17 backend confirmed live (pill=True for konrad); on-screen render pends operator rebuild
- [x] **Tooltip says stop/start, not restart** - the pill tooltip reads "A newer lab image is available locally - stop your server and start a new one to update"; a Docker restart reuses the existing container/image so it would NOT update
  - log: 2026-06-17 corrected from "restart ... to upgrade" in `ServerHero.tsx` + `MobileHome.tsx`; 2026-06-18 verb "upgrade"->"update" with the label rename
- [ ] **Runtime: pill clears after upgrade** - after stop/start onto the new image the running id == tag id -> pill disappears on the next `/activity` refresh
  - log: 2026-06-17 logic verified (`newer_lab_image_available(ref, latest_id)` -> False); live confirm pends rebuild

## Edge cases

- [x] **Edge: running image pruned/gone** - the running id is not inspectable/listed (rebuilt+pruned); pill still fires because the comparison never looks the running image up - it only needs the tag's current id and the running id (already held from the stats inspect)
  - log: 2026-06-17 this is THE live case (konrad) - now returns True
- [x] **Edge: running the current tag** - running id == tag id -> no pill
  - log: 2026-06-17 verified live (False when container runs `:latest`'s id)
- [x] **Edge: re-tag to older** - the lab tag points at an image that is NOT the repo's newest -> guard rejects -> no false pill
  - log: 2026-06-17 covered (test_no_upgrade_when_tag_retagged_to_older)
- [x] **Edge: docker unreachable** - snapshot is empty -> `tag_to_id.get(ref)` None -> no pill (conservative)
  - log: 2026-06-17 covered (except -> empty snapshot; test_no_upgrade_when_tag_unknown)
- [x] **Edge: container image id unknown** - stats returned no `image_id` -> no pill
  - log: 2026-06-17 covered (test_no_upgrade_when_container_unknown)
- [ ] **Edge: pinned non-latest tag with a newer sibling tag** - operator pins `:3.8.5` while a newer `:latest`/`:3.9.0` exists; the pinned tag is not the repo's newest so no pill - acceptable, since a restart spawns the pinned tag, not the sibling
  - log: 2026-06-17 documented; consequence of the newest-repo guard, intended for the watchtower `:latest` deployment

## API / functions

- `newer_lab_image_available(image_ref, container_image_id) -> bool` - resolves the ref, snapshots images, delegates to the pure helper
- `image_upgrade_available(latest_tag_id, container_image_id, newest_repo_id) -> bool` - pure: `latest_tag_id and container_image_id and latest_tag_id != container_image_id and latest_tag_id == newest_repo_id`
- `_image_snapshot_get() -> (tag_to_id, newest_id_by_repo)` - cached ~5min
- `_normalize_ref(image_ref) -> "repo:tag"` - implicit `:latest`, strips `@digest`
- `_parse_created(created) -> epoch float | None` - ISO-8601 string or epoch int
