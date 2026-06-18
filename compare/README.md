# Old-portal comparison

A hidden, throwaway **stock JupyterHub** container for comparing the original
portal design and functionality against the Duoptimum Hub portal. It runs the
unmodified `jupyterhub/jupyterhub` image (stock home / admin / user-management
UI) with dummy auth, bound to localhost only and joined to the live docker
network - never exposed to the internet, never routed through Traefik.

## Use

```bash
docker compose -f compare/compose.old-portal.yml up -d
# browse http://127.0.0.1:9444/  -> log in as `admin` (any password)
#   /hub/home   -> stock home (the page our portal home replaced)
#   /hub/admin  -> stock admin React app (the screen our Servers / Users replaced)
docker compose -f compare/compose.old-portal.yml down
```

Compare against the live portal at `https://jupyterhub.lab.stellars-tech.eu/`.

## Notes

- Dummy auth + no working spawner: the point is the UI/UX and feature surface,
  not running real labs
- Stateless: no volumes, its own in-container sqlite; remove with `down`
- Stock image version need not match exactly (5.4.x vs the live 5.5.0) - the
  stock UI is identical across the 5.x line for design comparison
