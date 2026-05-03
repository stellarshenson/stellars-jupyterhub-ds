# TLS Certificates

Two cert directories inside the hub container:

| Path | Role |
|---|---|
| `./certs/` (host) -> `/mnt/user_certs` (container, ro) | Operator-supplied yml + cert/key. Bind-mount is wired into `compose.yml` by default; populate `./certs/` next to the compose file to override. |
| `/mnt/certs` | Runtime dir Traefik scans (`--providers.file.directory=/mnt/certs --providers.file.watch=true`). Hub writes here. |

On startup, `00_provision_certificates.sh` decides which set Traefik will load:

| `/mnt/user_certs` | `/mnt/certs` (volume) | Action | Source |
|---|---|---|---|
| empty / missing | empty (first boot) | `mkcert.sh` + default `certs.yml` | auto-generated |
| empty / missing | has `*.crt`+`*.yml` from prior boot | use as-is | persisted |
| valid yml + referenced cert/key files exist | anything | wipe target's cert artifacts, copy operator files in, rewrite `/mnt/user_certs/`→`/mnt/certs/` in copied yml | operator-supplied |
| yml exists but cert/key missing | empty | log error, fall through to auto-generate | auto-generated |
| yml exists but cert/key missing | valid | log error, fall through to persisted | persisted |
| cert/key only, no yml | anything | yml required to use operator certs, fall through | persisted or auto-generated |

Operator-supplied path is all-or-nothing: any one yml with a missing reference rejects the whole operator set. Status is logged at startup as a banner — source label, every yml present, and per-cert subject / SAN / issuer / expiry.

## Supplying your own certs

Put your yml + cert/key in `./certs/` next to `compose.yml`. No compose changes needed - the bind-mount is wired into `compose.yml` by default. To point at a different host folder, override the volume in `compose_override.yml`:

```yaml
services:
  jupyterhub:
    volumes:
      - ../certs:/mnt/user_certs:ro
```

The folder must contain at least one yml file plus the cert/key it references. Example layout:

```
certs/
  tls.yml
  wildcard.lab.example.com.crt
  wildcard.lab.example.com.key
```

`tls.yml`:

```yaml
tls:
  stores:
    default:
      defaultCertificate:
        certFile: /mnt/certs/wildcard.lab.example.com.crt
        keyFile:  /mnt/certs/wildcard.lab.example.com.key
```

Path references can use `/mnt/user_certs/...`, `/mnt/certs/...`, or just the filename — all three resolve to the same file at validation time, and the copy step rewrites them so the yml is self-consistent in `/mnt/certs/`.

Multiple yml files are loaded by Traefik's directory provider, so multi-domain or split CA configs work — drop them all in `certs/`.

## Auto-generated path

When no operator certs are supplied, the hub generates a single self-signed RSA cert via `mkcert.sh` with:

- CN: `$CERTIFICATE_DOMAIN_NAME` (default `localhost`)
- 2048-bit key, 365-day validity, no SANs

Persists in the `jupyterhub_certs` Docker volume so subsequent restarts reuse it.

## Logs

Look for the `[Certificates]` prefix in hub startup logs:

```
[Certificates] applying operator certs from /mnt/user_certs
[Certificates] ========================================================
[Certificates] source: operator-supplied
[Certificates]   yml:    /mnt/certs/tls.yml
[Certificates]   cert:   /mnt/certs/wildcard.lab.example.com.crt
[Certificates]     subject: CN = *.lab.example.com
[Certificates]     SAN:     DNS:*.lab.example.com, DNS:lab.example.com
[Certificates]     issuer:  CN = Let's Encrypt Authority X3
[Certificates]     expires: Aug 12 14:55:00 2026 GMT
[Certificates] ========================================================
```

## File reference

| Path | Purpose |
|---|---|
| `services/jupyterhub/conf/bin/start-platform.d/00_provision_certificates.sh` | Decision tree at boot |
| `services/jupyterhub/conf/bin/mkcert.sh` | Self-signed generator (auto path) |
| `services/jupyterhub/templates/certs/certs.yml` | Default yml baked into image (referenced by auto path) |
| `compose.yml` `jupyterhub_certs` / `jupyterhub_user_certs` | Runtime + operator volumes |
