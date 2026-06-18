# Acceptance Criteria - Cert Provisioning

Hub provisions Traefik TLS at boot via `00_provision_certificates.sh`, reconciling the `/user-certs` overlay against the `/certs` runtime volume and choosing operator > persisted > auto. `/certs` is the dir Traefik scans; copying the overlay into the volume makes operator certs survive a failed host-bind mount across restarts.

- [x] **Runtime dir `/certs`** - `CERTIFICATE_TARGET_DIR` default `/certs`; Traefik file provider scans it (`watch=true`); hub writes here; backed by the `jupyterhub_certs` named volume
  - log: 2026-06-17 implemented + grep-verified no legacy path remains
- [x] **Overlay `/user-certs`** - `CERTIFICATE_USER_CERTS_DIR` default `/user-certs`; read-only host bind of `./certs`; optional - missing/empty means no operator certs
  - log: 2026-06-17 renamed from `/mnt/user_certs`
- [x] **No legacy `/mnt` cert paths** - no `/mnt/certs` or `/mnt/user_certs` in compose, Dockerfile, script, config, docs; historical JOURNAL entries exempt
  - log: 2026-06-17 swept both repos, clean
- [x] **Operator tier** - `/user-certs` has >=1 `*.yml`/`*.yaml` AND every `certFile`/`keyFile`/`caFile` resolves to an existing file -> source `operator-supplied`
  - log: 2026-06-17 verified by simulation
- [x] **Operator copy + rewrite** - delete top-level cert artifacts in `/certs`, `cp -a` overlay into `/certs` (subdirs included), sed-rewrite `/user-certs/` -> `/certs/` in copied yml so paths stay self-consistent
  - log: 2026-06-17 unchanged behaviour, paths migrated
- [x] **Persisted tier (symmetric)** - overlay empty/invalid AND `/certs` has >=1 yml whose every referenced file exists (recursive descent, `.pem` + subdirs accepted) -> keep `/certs` as-is, source `persisted`
  - log: 2026-06-17 rewritten from the old top-level-`*.crt`-only check; verified by simulation
- [x] **Auto tier** - operator + persisted both invalid -> `mkcert.sh` self-signed (CN `$CERTIFICATE_DOMAIN_NAME`, 2048-bit, 365d, no SAN) + default `certs.yml` into `/certs`, source `auto-generated`
  - log: 2026-06-17 unchanged, target path migrated
- [x] **Tier precedence** - operator > persisted > auto, evaluated in that order
  - log: 2026-06-17 verified
- [x] **All-or-nothing set** - a single missing reference rejects the whole tier's set and falls through to the next tier
  - log: 2026-06-17 verified
- [x] **Path resolution** - `resolve_under(dir,path)`: paths under `/user-certs` or `/certs` both remap under `dir`; other absolute pass through; bare/relative go under `dir`; used by operator (dir=`/user-certs`) and persisted (dir=`/certs`)
  - log: 2026-06-17 generalised from single-dir `resolve_user_path`
- [x] **Status banner** - startup logs `[Certificates]` source label, every yml present, per-cert subject/SAN/issuer/expiry (per-cert detail globs `*.crt` only, so `.pem` certs log the yml but not subject - cosmetic)
  - log: 2026-06-17 banner unchanged; `.pem` cosmetic gap noted
- [ ] **Resilience: failed host mount** - overlay fails to mount on restart (empty) + valid copy in `/certs` volume -> persisted serves the wildcard, not self-signed
  - log: 2026-06-17 logic verified by simulation; end-to-end pending live rebuild
- [x] **Resilience: `.pem` subdir recognised** - operator wildcard stored as `_.x/cert.pem` recognised by the persisted tier
  - log: 2026-06-17 the fix that closes the original clobber bug
- [x] **Resilience: no clobber** - a valid volume copy is never overwritten by auto-generate
  - log: 2026-06-17 falls out of the symmetric persisted check
- [x] **Direct-SSL mode** - `JUPYTERHUB_SSL_ENABLED=1` uses `/certs/server.crt` + `/certs/server.key`
  - log: 2026-06-17 path migrated
- [x] **Image bake** - Dockerfile `ENV CERTIFICATE_TARGET_DIR=/certs` + `CERTIFICATE_USER_CERTS_DIR=/user-certs`; `COPY templates/certs -> /certs`
  - log: 2026-06-17 added target env, migrated COPY
- [x] **Compose wiring** - `jupyterhub_certs:/certs` (hub + traefik), `./certs:/user-certs:ro` (hub overlay), provider dir `/certs`
  - log: 2026-06-17 migrated
- [x] **Functional test mount** - `tests/functional` compose mounts `certs:/certs`
  - log: 2026-06-17 migrated
- [x] **Wrapper certs.yml** - operator yml uses `/certs/...` paths; comment references the `/user-certs` overlay
  - log: 2026-06-17 reverted to `/certs`, comment updated
- [x] **Wrapper Traefik mount** - `./certs:/certs:ro` retained (host bind; Traefik reads `/certs`); deliberate, not changed
  - log: 2026-06-17 confirmed correct per operator
- [x] **Docs** - `docs/certificates.md` covers two dirs, three tiers, resilience rationale, path rules, reverse-proxy variant, logs, file reference
  - log: 2026-06-17 rewritten

- [x] **Edge: first boot, both empty** - empty overlay + empty volume -> auto-generate
  - log: 2026-06-17 verified by simulation
- [x] **Edge: yml present, cert/key missing** - operator invalid (logged) -> fall to persisted, else auto
  - log: 2026-06-17 covered by all-or-nothing
- [x] **Edge: cert/key present, no yml** - no yml in dir -> tier invalid -> fall through (yml required)
  - log: 2026-06-17 covered by the yml-count guard
- [ ] **Edge: corrupt / unparseable yml** - `yq` error -> `extract_paths` empty -> zero refs -> currently treated as valid (set copied/kept); Traefik then logs a parse error and keeps last-good
  - log: 2026-06-17 current behaviour documented; harden (reject yml yielding no refs)? confirm desired behaviour
- [x] **Edge: yml with no cert refs** - tls-options-only yml -> zero refs -> valid; loaded as Traefik config, no cert asserted (same semantics both tiers)
  - log: 2026-06-17 accepted as-is
- [x] **Edge: multiple yml files** - all loaded by the directory provider (multi-domain / split-CA)
  - log: 2026-06-17 unchanged
- [x] **Edge: subdir / `.pem` layout** - copied via `cp -a` and validated via recursive extract + resolve
  - log: 2026-06-17 verified by simulation

## Verification

- [x] **Unit/import tests** - `make test` = 556 (hub-services) + 63 (docker-proxy) pass
  - log: 2026-06-17 green
- [x] **Script syntax** - `bash -n` clean
  - log: 2026-06-17 ok
- [x] **Persisted simulation** - operator-valid; persisted recognises `.pem`-subdir wildcard; empty volume -> auto (no false-persist)
  - log: 2026-06-17 passed
- [ ] **Live end-to-end** - rebuild + restart: banner shows `operator-supplied`; a forced empty-overlay restart still serves the wildcard via persisted
  - log: 2026-06-17 pending user rebuild

## Env

- `CERTIFICATE_TARGET_DIR` (default `/certs`) - runtime dir Traefik scans
- `CERTIFICATE_USER_CERTS_DIR` (default `/user-certs`) - operator overlay
- `CERTIFICATE_DOMAIN_NAME` (default `localhost`) - CN for the auto-generated cert
