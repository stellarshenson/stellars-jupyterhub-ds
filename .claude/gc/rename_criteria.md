# Rename `stellars_hub` -> `stellars-hub-services` / `stellars_hub_services`

## Targets

| Layer | Before | After |
|---|---|---|
| Subproject directory | `services/jupyterhub/stellars_hub/` | `services/jupyterhub/stellars-hub-services/` |
| pyproject `name` | `stellars-hub` | `stellars-hub-services` |
| Python package directory | `services/jupyterhub/stellars_hub/stellars_hub/` | `services/jupyterhub/stellars-hub-services/stellars_hub_services/` |
| Python import / module string | `stellars_hub` | `stellars_hub_services` |
| Wheel artifact name | `stellars_hub-*.whl` | `stellars_hub_services-*.whl` (hatchling derives from `name`) |

Version (`3.8.0` in the subproject's `__init__.py`) and the parent project version (`3.10.15` in top-level `pyproject.toml`) are untouched.

## Replacement plan

Two distinct string swaps, applied in this order to avoid `stellars_hub` -> `stellars_hub_services_services` on a re-run:

1. **`stellars-hub`** (dash) -> **`stellars-hub-services`**: pyproject name field, docs, Dockerfile, Makefile, README, CI workflow.
2. **`stellars_hub`** (underscore, word-boundary `\b`) -> **`stellars_hub_services`**: every `import stellars_hub`, `from stellars_hub`, `python -m stellars_hub...`, route-class lookup strings, `__init__.py` re-exports.

Both swaps use `grep -wln` or `git ls-files | xargs sed -i` with word-boundary anchors so they are idempotent.

## Sites that must change

- `services/jupyterhub/stellars_hub/pyproject.toml` -> `name`
- `services/jupyterhub/stellars_hub/Makefile` -> targets that name the package
- `services/jupyterhub/stellars_hub/stellars_hub/**/*.py` (all source files inside)
- `services/jupyterhub/stellars_hub/tests/**/*.py` (all test files)
- `services/jupyterhub/Dockerfile.jupyterhub` -> `COPY` paths, `python -m build`, `uv pip install`, `pip install /tmp/...whl`, `pytest /src/.../tests/`
- `config/jupyterhub_config.py` -> import block + any inline `python -m stellars_hub...` invocation
- `services/jupyterhub/html_templates_enhanced/{home,admin}.html` -> string mentions only (likely just attribution / package label)
- `docs/*.md` (7 files) and `README.md` -> all narrative mentions of `stellars_hub` / `stellars-hub`
- `services/jupyterhub/stellars-docker-proxy/` docs (e.g. `docs/limited-docker-access.md`) that reference `stellars_hub.docker_proxy`

## Sites that must NOT change

- `services/jupyterhub/stellars-docker-proxy/` package source - it is JupyterHub-agnostic by design; it does not import from stellars_hub, only the orchestration in stellars_hub imports from it.
- `.claude/JOURNAL.md` historical entries (append-only history).
- `.claude/gc/agent-*.md` reports (history of what was named at the time).
- `.claude/CLAUDE.md` (no project-name dependency in its rules).
- `.claude/settings.local.json` runtime allowlist - touching it may invalidate previously-approved tool calls; treat as opaque.

## Verification gates (executed in order)

1. **Directory + package rename via `git mv`** (preserves history):
   - `git mv services/jupyterhub/stellars_hub services/jupyterhub/stellars-hub-services`
   - `git mv services/jupyterhub/stellars-hub-services/stellars_hub services/jupyterhub/stellars-hub-services/stellars_hub_services`
2. **String swaps** in remaining files (Dockerfile, config, docs, tests, source under the renamed dirs):
   - First `stellars-hub` -> `stellars-hub-services` (dash form), then `stellars_hub` -> `stellars_hub_services` (underscore form, word-boundary).
3. **AST compile**: `python -m py_compile` on every `*.py` under the rename target.
4. **Static import audit**: zero remaining `stellars_hub\b` or `stellars-hub\b` (not followed by `-services`) anywhere in the live tree.
5. **stellars_hub_services tests**: `cd services/jupyterhub/stellars-hub-services && uv pip install -e . && python -m pytest tests/ -q` -> 168 passing.
6. **stellars-docker-proxy tests** (unchanged but must still pass): `pytest tests/ -q` -> 26 passing.
7. **Wheel build** smoke: `python -m build services/jupyterhub/stellars-hub-services --outdir /tmp/wheels` produces `stellars_hub_services-3.8.0-*.whl`. Do NOT run `make build` (it's a full docker build).
8. **Dockerfile dry-parse**: `docker build --dry-run` is not portable; instead grep for any remaining `stellars_hub` (sans `_services`) in `Dockerfile.jupyterhub` after the swap -> zero hits.

## Rollback

The pre-GC checkpoint `CHECKPOINT_BEFORE_GC_3.10.15` covers this rename too (the GC and the rename happen on the same branch after the checkpoint).

## What "done" looks like

- Tests: 168 stellars_hub_services + 26 stellars-docker-proxy = 194 passing.
- Wheel: hatchling produces `stellars_hub_services-3.8.0-py3-none-any.whl`.
- Grep: no live file references `stellars_hub\b` or `stellars-hub\b` (only `stellars_hub_services` / `stellars-hub-services` / `stellars-docker-proxy`).
- Image rebuild gates (Dockerfile builder stage): `python -m build /src/stellars-hub-services`, `pip install /dist/stellars_hub_services-*.whl`, `pytest /src/stellars-hub-services/tests/`.

## Out of scope

- Parent project (`stellars-jupyterhub-ds` repo, version 3.10.15) keeps its name and version.
- The `stellars-docker-proxy` package keeps its name and module (`stellars_docker_proxy`).
- Documentation rewrites beyond name swaps (terse content stays terse).
