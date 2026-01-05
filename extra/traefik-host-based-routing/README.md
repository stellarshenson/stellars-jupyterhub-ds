# Traefik Host-Based Routing Template

Template for deploying stellars-jupyterhub-ds with local Traefik reverse proxy and self-signed certificates.

## Quick Start

1. Copy this folder to create a new deployment:
   ```bash
   cp -r extra/traefik-host-based-routing /path/to/<name>_stellars_jupyterhub_ds
   cd /path/to/<name>_stellars_jupyterhub_ds
   ```

2. Generate certificates for your domain:
   ```bash
   ./generate-certs.sh yourdomain.example.com
   ```

3. Edit `compose_override.yml` - replace `YOURDOMAIN` with your domain

4. Start:
   ```bash
   ./start.sh
   ```

## Structure

```
<name>_stellars_jupyterhub_ds/
  compose_override.yml          # Local Traefik + JupyterHub config
  start.sh                      # Pull latest + start services
  stop.sh                       # Stop services
  generate-certs.sh             # Certificate generation script
  certs/
    tls.yml                     # Traefik TLS configuration
    _.yourdomain.example.com/   # Generated wildcard cert
      cert.pem                  # Certificate (import to browser)
      key.pem                   # Private key
  stellars-jupyterhub-ds/       # Cloned repository (gitignored)
```

## Configuration

Edit `compose_override.yml` to customize:
- Domain name (replace `YOURDOMAIN` placeholder)
- Ports (default: 80/443)
- Network name
- Additional services

## Access

After deployment:
- JupyterHub: https://jupyterhub.yourdomain.example.com/
- Traefik: https://traefik.yourdomain.example.com

Import `certs/_.<domain>/cert.pem` to browser for trusted HTTPS.

## Commands

```bash
./start.sh    # Pull latest + start services
./stop.sh     # Stop all services
```

To view logs:
```bash
docker compose -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml logs -f jupyterhub
```
