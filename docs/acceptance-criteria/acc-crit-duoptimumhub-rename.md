# Acceptance Criteria - duoptimumhub service + image rename

The hub's Docker Compose service is renamed `jupyterhub` -> `duoptimumhub` and the published image `stellars/stellars-jupyterhub-ds` -> `stellars/duoptimumhub`, so the deployment matches the Duoptimum Hub branding and the DockerHub push targets the new repo. The hub's URL prefix (`/jupyterhub`, `JUPYTERHUB_BASE_URL`) and all `JUPYTERHUB_*` env vars are unchanged - only the compose service identity and the image tag move. Verified against the code 2026-06-18.

## Compose service rename

- [x] **Service key** - `compose.yml` hub service is `duoptimumhub` (was `jupyterhub`)
  - log: 2026-06-18 operator: "rename jupyterhub service to duoptimumhub"
- [x] **depends_on updated** - traefik and watchtower `depends_on` point at `duoptimumhub` (a stale `jupyterhub` reference would fail compose validation)
  - log: 2026-06-18 both blocks renamed
- [x] **Traefik identifiers** - router/service/middleware renamed `jupyterhub-rtr`/`jupyterhub-svc`/`jupyterhub-ratelimit` -> `duoptimumhub-*`, consistently in `compose.yml` and the wrapper override
  - log: 2026-06-18 the `routers.X.service` reference still matches the service definition
- [x] **URL path unchanged** - the router rule still matches `Path(/jupyterhub)`; the deploy prefix is a separate concern from the service name and was not touched
  - log: 2026-06-18 base_url stays `/jupyterhub`
- [x] **container_name** - the literal suffix is `-duoptimumhub` (`${COMPOSE_PROJECT_NAME:-…}-duoptimumhub`)
  - log: 2026-06-18 renamed; project-name default unchanged
- [x] **Hub bind/connect host** - `c.JupyterHub.hub_ip` and `hub_connect_url` in `config/jupyterhub_config.py` use `duoptimumhub`; the hub binds to, and CHP / spawned labs reach the hub by, the compose service name
  - log: 2026-06-18 the first rebuild crashed boot with `getaddrinfo ENOTFOUND jupyterhub` (hub_ip still hardcoded the old name); fixed both lines to `duoptimumhub`

## Image rename

- [x] **Image tag** - the hub image is `stellars/duoptimumhub` everywhere it is built, tagged, pulled or referenced: Makefile (`HUB_IMAGE`, build `--tag`, `tag`, push, success banners), `compose.yml`, the functional compose, `start.sh`, `start.bat`
  - log: 2026-06-18 operator: "change the image name ... to duoptimumhub ... so the dockerhub push won't blow up"; chose `stellars/duoptimumhub`
- [x] **README DockerHub badges** - image-size and pulls badges point at `stellars/duoptimumhub`
  - log: 2026-06-18 GitHub repo URLs left as-is (repo not renamed)
- [x] **Only the hub image** - the gpuinfo (`stellars/stellars-gpuinfo-nvidia`) and lab (`stellars/stellars-jupyterlab-ds`) images are unchanged (no `jupyterhub` token)
  - log: 2026-06-18 scope limited to the hub image

## Collaterals (verified independent)

- [x] **gpuinfo sidecar unaffected** - the hub finds the sidecar by its own DNS name (`gpuinfo-nvidia`) and joins the sidecar network by container id, never by the hub's compose service name; zero changes needed
  - log: 2026-06-18 `gpuinfo_sidecar.py` uses the Docker socket + URL host, not the service name
- [x] **Networks/volumes unchanged** - network and volume names derive from `COMPOSE_PROJECT_NAME`, not the service name
  - log: 2026-06-18 `${COMPOSE_PROJECT_NAME:-…}_network`, named volumes independent

## Tests + harness

- [x] **Functional harness renamed** - the service is `duoptimumhub` in all three harness compose files; `conftest.py` `BASE_URL`/`HUB_HOST` default to `duoptimumhub`; the Makefile `--wait`/`restart` targets name `duoptimumhub`
  - log: 2026-06-18 operator: "fix the tests and harness"
- [ ] **Functional suites pass post-rebuild** - `make test-functional` and `make test-functional-env` are green against the rebuilt `stellars/duoptimumhub:latest` image
  - log: 2026-06-18 needs the authorised one-time `make rebuild`

## Deployment surfaces

- [x] **Wrapper override + compose** - `../compose.yml` refreshed from the submodule; `../compose_override.yml` service + traefik + branding-env names renamed
  - log: 2026-06-18 operator: "copy current compose.yml to .. and fix ../compose-override.yml"
- [x] **Copier template** - `copier-stellars-jupyterhub-ds` override `.jinja` service key + traefik + image comment renamed; `tests/test_render.sh` assertions updated
  - log: 2026-06-18 operator: "fix the template - it refers to all the old setup and env names"

## Edge cases

- [x] **Edge: GitHub repo URLs preserved** - `github.com/.../stellars-jupyterhub-ds` and `copier-stellars-jupyterhub-ds` URLs are the repo, not the image, and are left unchanged
  - log: 2026-06-18 only `stellars/stellars-jupyterhub-ds` (image) renamed, not `…henson/stellars-jupyterhub-ds`
- [ ] **Edge: live recreate required** - a running stack must be recreated (`down`/`up`) to pick up the new service + container name; `make start` uses `--no-recreate` and will not rename a running container in place
  - log: 2026-06-18 operator action; not auto-applied
- [x] **Edge: historical docs untouched** - `CHANGELOG.md`, `docs/medium/*`, and journals keep the old names (they record past state)
  - log: 2026-06-18 append-only / published article content
