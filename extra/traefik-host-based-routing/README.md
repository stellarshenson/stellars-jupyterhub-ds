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

3. Create `.env` and set your hostname:
   ```bash
   cp .env.example .env
   # Edit .env: HOSTNAME=yourdomain.example.com
   ```

4. Start:
   ```bash
   ./start.sh
   ```

## Structure

```
<name>_stellars_jupyterhub_ds/
  compose_override.yml          # Local Traefik + JupyterHub config
  compose_cifs.yml              # Optional CIFS mount configuration
  start.sh                      # Clone/update + start services
  stop.sh                       # Stop services
  generate-certs.sh             # Certificate generation script
  install_cert.sh               # Linux certificate installer
  install_cert.bat              # Windows certificate installer
  .env.example                  # Example environment config
  certs/
    tls.yml                     # Traefik TLS configuration
    _.yourdomain.example.com/   # Generated wildcard cert
      cert.pem                  # Certificate (import to browser)
      key.pem                   # Private key
  stellars-jupyterhub-ds/       # Cloned repository (gitignored)
```

## Configuration

Set `HOSTNAME` in `.env` for your domain. Edit `compose_override.yml` to customize:
- Ports (default: 80/443)
- Environment variables (idle culler, signup)
- Network name

### Optional CIFS Mount

To enable shared NAS storage for user containers:

1. Edit `compose_cifs.yml` with your NAS credentials
2. Create `.env` from `.env.example`:
   ```bash
   cp .env.example .env
   ```
3. Set `ENABLE_CIFS=1` in `.env`

## Access

After deployment:
- JupyterHub: https://jupyterhub.yourdomain.example.com/
- Traefik: https://traefik.yourdomain.example.com

### Certificate Installation

Import the self-signed certificate to your browser for trusted HTTPS:

**Linux:**
```bash
./install_cert.sh certs/_.yourdomain.example.com/
```

**Windows:**
```cmd
install_cert.bat certs\_.yourdomain.example.com\
```

## Commands

```bash
./start.sh             # Clone repo (if missing) + start services
./start.sh --refresh   # Pull latest upstream + start services
./stop.sh              # Stop all services
```

To view logs:
```bash
docker compose -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml logs -f jupyterhub
```
