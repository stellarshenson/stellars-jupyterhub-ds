# TLS Certificates

The hub provisions Traefik's certificates at boot via `00_provision_certificates.sh`, run from `/start-platform.d/`. The script reconciles two directories and picks one of three sources, so a deployment serves operator certs when supplied, the last-known set across restarts, and a self-signed fallback otherwise - without manual Traefik surgery.

## The two directories

- **`/user-certs`** - operator overlay, read-only. A host bind of `./certs` (next to `compose.yml`). Optional: missing or empty means no operator certs
- **`/certs`** - runtime dir, read-write. The `jupyterhub_certs` named volume. Traefik's file provider scans it (`--providers.file.directory=/certs --providers.file.watch=true`); the hub writes here

Paths are env-overridable: `CERTIFICATE_USER_CERTS_DIR` (default `/user-certs`), `CERTIFICATE_TARGET_DIR` (default `/certs`).

## The decision

Three tiers, highest first. The chosen source is logged as a `[Certificates]` banner.

| `/user-certs` (overlay) | `/certs` (runtime volume) | Action | Source |
|---|---|---|---|
| valid - at least one yml, every referenced file exists | any | wipe top-level cert files in `/certs`, copy the overlay in, rewrite `/user-certs/`->`/certs/` in copied yml | operator-supplied |
| empty / invalid | valid - at least one yml, every referenced file exists | keep as-is | persisted |
| empty / invalid | empty / invalid | `mkcert.sh` + default `certs.yml` | auto-generated |

Both the operator and persisted checks are the same validation, rooted at their own directory: at least one `*.yml`/`*.yaml`, and every `certFile`/`keyFile`/`caFile` it references (extracted recursively, subdirectories and `.pem` included) must resolve to a real file. It is all-or-nothing - a single missing reference rejects the whole set and falls through to the next tier.

## Why the overlay is copied into the volume

The overlay is a host bind. If the host folder fails to mount on a restart - which docker-compose does silently, leaving the overlay empty - the operator tier is skipped. The persisted tier then serves the copy already in the `jupyterhub_certs` volume, so TLS survives a missing host mount instead of dropping to a self-signed `localhost` cert. Because the persisted check validates the same way the operator tier does, a real wildcard stored as `_.example.com/cert.pem` is recognised across the restart and never clobbered by the auto-generate fallback.

## Supplying your own certs

Put a yml plus its cert/key in `./certs/` next to `compose.yml` - the bind-mount is wired in by default. To point at a different host folder, override the overlay in `compose_override.yml`:

```yaml
services:
  jupyterhub:
    volumes:
      - ../my-certs:/user-certs:ro
```

The folder needs at least one yml plus the cert/key it references. Example:

```
certs/
  tls.yml
  _.lab.example.com/cert.pem
  _.lab.example.com/key.pem
```

`tls.yml`:

```yaml
tls:
  stores:
    default:
      defaultCertificate:
        certFile: /certs/_.lab.example.com/cert.pem
        keyFile:  /certs/_.lab.example.com/key.pem
```

Path references can be written as `/certs/...` (what Traefik ultimately sees), `/user-certs/...`, or a bare filename - all resolve to the same file during validation, and the copy step rewrites them so the yml stays self-consistent under `/certs/`. Multiple yml files are loaded by the directory provider, so multi-domain or split-CA layouts work - drop them all in `certs/`.

## Auto-generated fallback

When no operator or persisted certs exist, `mkcert.sh` writes a self-signed RSA cert plus a default `certs.yml` into `/certs`:

- CN `$CERTIFICATE_DOMAIN_NAME` (default `localhost`)
- 2048-bit key, 365-day validity, no SANs

It persists in the `jupyterhub_certs` volume, so the next boot reuses it via the persisted tier rather than regenerating.

## Reverse-proxy variant

A wrapper deployment may bind the host cert folder straight into the proxy (`./certs:/certs:ro`) and point the file provider there, so the proxy serves the host folder live and hot-reloads edits. The hub still runs the same provisioning into its own `jupyterhub_certs` volume; in that topology the volume copy is hub-side validation and last-known state rather than the proxy's serving path.

## Logs

Look for the `[Certificates]` prefix at hub startup:

```
[Certificates] applying operator certs from /user-certs
[Certificates] ========================================================
[Certificates] source: operator-supplied
[Certificates]   yml:    /certs/tls.yml
[Certificates]   cert:   /certs/_.lab.example.com/cert.pem
[Certificates]     subject: CN = *.lab.example.com
[Certificates]     SAN:     DNS:*.lab.example.com, DNS:lab.example.com
[Certificates]     issuer:  CN = Let's Encrypt Authority X3
[Certificates]     expires: Aug 12 14:55:00 2026 GMT
[Certificates] ========================================================
```

## File reference

| Path | Purpose |
|---|---|
| `services/jupyterhub/conf/bin/start-platform.d/00_provision_certificates.sh` | Provisioning decision tree at boot |
| `services/jupyterhub/conf/bin/mkcert.sh` | Self-signed generator (auto-generated tier) |
| `services/jupyterhub/templates/certs/certs.yml` | Default yml baked into the image (referenced by the auto path) |
| `compose.yml` - `jupyterhub_certs` volume at `/certs`; `./certs:/user-certs:ro` bind | Runtime volume + operator overlay |
