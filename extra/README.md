Additional tools and scripts that help with the hub maintenance

- `docker_volume_backupper` - script that backs docker volumes (use regex for name)
- `volume-renamer` - scripts to rename volumes and migrate user data between usernames

Cert generation, install scripts, and the local-Traefik deployment scaffolding live in the [stellars-jupyterhub-ds-deployment-template](https://github.com/stellarshenson/stellars-jupyterhub-ds-deployment-template) Copier template - the cert tooling is rendered into every generated deployment under `certs/` (per-deployment scripts) and also lives standalone in the template repo at `extra/certs-installer/` for OS root-trust-store installation.


