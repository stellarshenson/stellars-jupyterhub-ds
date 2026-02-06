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
   ./generate-certs.sh --cn "My DEV Certificate" --dns-altnames "*.example.com,example.com,*.localhost,localhost"
   ```

3. Configure (optional):
   ```bash
   # Create .env to override defaults from .env.default:
   echo "BASE_HOSTNAME=example.com" > .env
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
  generate-certs.sh             # Certificate generation (--help for usage)
  install_cert.sh               # Linux certificate installer
  install_cert.bat              # Windows certificate installer
  .env.default                  # Default environment config (always loaded)
  .env                          # Local overrides (optional, gitignored)
  certs/
    <prefix>.tls.yml            # Traefik TLS configuration (auto-generated)
    <prefix>/                   # Certificate folder (auto-generated)
      cert.pem                  # Certificate (import to browser)
      key.pem                   # Private key
  stellars-jupyterhub-ds/       # Cloned repository (gitignored)
```

## Configuration

Configure via `.env.default` (always loaded) and `.env` (optional overrides, gitignored):

- `BASE_HOSTNAME` - domain for Traefik routing (default: `localhost`)
- `JUPYTERHUB_PREFIX` - JupyterHub subdomain prefix, set empty to serve at root domain (default: `jupyterhub.`)
- `ENABLE_CIFS` - enable CIFS shared mount, `0`/`1` (default: `0`)

Edit `compose_override.yml` to customize ports (default: 80/443), environment variables (idle culler, signup), or network name.

### Optional CIFS Mount

1. Edit `compose_cifs.yml` with your NAS credentials
2. Set `ENABLE_CIFS=1` in `.env`

## Access

After deployment:
- JupyterHub: `https://${JUPYTERHUB_PREFIX}${BASE_HOSTNAME}/` (default: `jupyterhub.localhost`)
- Traefik: `https://traefik.${BASE_HOSTNAME}/`
- Localhost: `https://jupyterhub.localhost/`, `https://jupyterhub.app.localhost/`

### Certificate Installation

Import the self-signed certificate to your browser for trusted HTTPS:

**Linux:**
```bash
./install_cert.sh certs/<prefix>/
```

**Windows:**
```cmd
install_cert.bat certs\<prefix>\
```

## Commands

```bash
./start.sh             # Clone repo (if missing) + start services
./start.sh --refresh   # Pull latest upstream + start services
./stop.sh              # Stop all services
```

To view logs:
```bash
docker compose --env-file .env.default -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml logs -f jupyterhub
```
