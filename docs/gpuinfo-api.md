# GPU-info sidecar API

The hub container has no GPU access of its own. Instead of spawning a throwaway `nvidia/cuda` container on every probe (a ~1-3s spin each cycle), it queries a long-running sidecar over HTTP on a dedicated docker network. The sidecar runs the vendor tool (`nvidia-smi` today) in one warm process and answers in milliseconds. The HTTP contract is deliberately vendor-neutral so future `gpuinfo-amd` / `gpuinfo-intel` / `gpuinfo-applesilicon` peers can answer the same shape.

- Service: `services/jupyterhub/gpuinfo-nvidia` (FastAPI + uvicorn, stdlib `subprocess` to `nvidia-smi`)
- Image: `stellars/stellars-gpuinfo-nvidia:latest`, run with `--runtime=nvidia`
- Two read-only, side-effect-free endpoints; always 200 while the process is up, even on a GPU-less host
- Consumer: the hub (`duoptimum-hub-services`), never the spawned user labs (sidecar sits on a hub-only network)

## Endpoints

- `GET /health` -> liveness + whether the driver is usable
- `GET /gpus` -> the full inventory + a live health snapshot

`GET /health`

```json
{ "status": "ok", "vendor": "nvidia", "driver_available": true }
```

`driver_available` is `false` when the vendor tool cannot be queried (no driver, no GPU); the endpoint still returns 200 so the hub's health-gated dependency is satisfied on GPU-less hosts.

`GET /gpus`

```json
{
  "vendor": "nvidia",
  "available": true,
  "count": 2,
  "timestamp": "2026-06-18T09:10:24.398000+00:00",
  "gpus": [
    {
      "index": "0",
      "name": "NVIDIA RTX A5000",
      "uuid": "GPU-2b9c...",
      "utilization": 37,
      "memory_used_mb": 1493,
      "memory_total_mb": 24564,
      "temperature_c": 41,
      "power_w": 71.2,
      "processes": [ { "pid": 12345, "name": "python", "used_memory_mb": 1402 } ]
    }
  ]
}
```

`available` is `false` (and `gpus` empty) when the driver/tooling is missing.

## Schema

The contract is shared across all sidecar implementations. A field a backend cannot report is returned `null`, never omitted, so the hub parses one stable shape regardless of which sidecar answers. Units are in the field names.

| Field | Type | Meaning |
|-------|------|---------|
| `index` | string | Vendor-local GPU index ("0", "1", ...) |
| `name` | string \| null | Marketing/model name |
| `uuid` | string \| null | Vendor-unique id; the stable key for process attribution |
| `utilization` | int \| null | Core utilisation percent; `null` = backend has no counter (distinct from `0` = idle) |
| `memory_used_mb` | int \| null | Used framebuffer memory in MB |
| `memory_total_mb` | int \| null | Total framebuffer memory in MB |
| `temperature_c` | int \| null | Core temperature in Celsius |
| `power_w` | float \| null | Current board power draw in Watts |
| `processes[]` | list | Compute processes holding the GPU - `{pid, name, used_memory_mb}`; the hook for attributing load to a user |

`GpuReport` wraps the list with `vendor`, `available`, `count`, `timestamp`. `Health` is `{status, vendor, driver_available}`.

## How the hub consumes it

- **Client** (`gpu_client.py`) - stdlib `urllib`, so it runs in the sync thread pool. `fetch_payload()` returns the `/gpus` dict or `None` on any failure; `fetch_payload_with_retry()` blocks at startup only while the sidecar is unreachable (a zero-GPU answer is authoritative, returned immediately)
- **Detection** (`gpu.py`) - `resolve_gpu_mode(gpu_enabled)` maps `JUPYTERHUB_GPU_ENABLED` (`0` off, `1` forced, `2` auto-detect) to a grant + inventory. Auto-detect derives presence from the inventory; a cold/slow sidecar falls back to the last-known inventory persisted on the data volume rather than dropping to off
- **Utilisation cache** (`gpu_cache.py`) - `GpuUtilizationRefresher` keeps a warm snapshot on a Tornado `PeriodicCallback`, refreshing every `JUPYTERHUB_GPU_UTIL_UPDATE_INTERVAL` seconds (default 30); `/activity` reads the snapshot non-blocking
- **Lifecycle** (`gpuinfo_sidecar.py`) - the hub self-starts the sidecar over the docker socket (recreate-fresh every boot from the current image) and removes it at exit, so it works the same regardless of which compose project launched the hub. The sidecar is also DECLARED as a profiled compose service (`gpuinfo` profile, never auto-started) so `docker compose build` produces its image locally; the hub joins the compose-declared `hub_gpuinfo_network` (discovered by its `duoptimum.gpuinfo.network` label) rather than creating it
- **Env**: `JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME` (default `gpuinfo-nvidia`), `JUPYTERHUB_GPUINFO_NVIDIA_URL` (default `http://{hostname}:8000`, where `{hostname}` is filled at boot with the address the hub discovers for the running sidecar), `JUPYTERHUB_GPUINFO_NVIDIA_IMAGE`, `JUPYTERHUB_GPU_UTIL_UPDATE_INTERVAL`. The hub-to-sidecar network is discovered by label, not named via an env (`JUPYTERHUB_GPUINFO_NETWORK_NAME` is an optional override)

## Vendor-neutrality assessment

The DATA CONTRACT is already well-designed for multiple vendors and needs only additive changes. The vendor coupling that actually blocks a second backend lives in the hub-side LAUNCH and in the single-sidecar assumption, not in the wire schema.

Already generic:

- Shared `schema.py` contract with a `vendor` field on every response
- Optional fields returned as `null` (not omitted), and `null` (unsupported) is distinct from `0` (measured idle)
- Units baked into field names (`_mb`, `_w`, `_c`) - no unit ambiguity across backends
- Read-only, side-effect-free endpoints that stay 200 on GPU-less hosts
- The hub consumer (`gpu_client`, `gpu.py`, `gpu_cache`) is written against the contract, not against nvidia - it already speaks of amd/intel/applesilicon peers

Gaps and recommendations (proposals - not implemented):

- **Per-GPU `vendor` field** - `vendor` is only report-level. A merged inventory from two sidecars loses attribution, and `index` collides (both vendors start at "0"). Add `vendor` to each `Gpu` and treat `vendor:index` (or `uuid`) as the global key. Additive, low risk
- **Contract `api_version`** - the only version on the wire is the package version. Add an explicit `api_version` to `GpuReport`/`Health` so the hub can tolerate a sidecar built from a different release. Additive
- **Multi-sidecar / mixed-vendor hosts** - `JUPYTERHUB_GPUINFO_URL` is a single URL, so a host with NVIDIA + AMD (or + Apple) cannot be represented; only one sidecar answers. Minimal fix: let the client accept a comma-separated list of URLs and union the `gpus[]` (the client already tolerates `[]` per source). Larger option: an aggregator sidecar that fans out and merges
- **Vendor-generic lifecycle** - the real blocker. `ensure_gpuinfo_sidecar` hardcodes `runtime='nvidia'` and `NVIDIA_VISIBLE_DEVICES`/`NVIDIA_DRIVER_CAPABILITIES`. AMD needs `/dev/kfd` + `/dev/dri` device mounts (no nvidia runtime); Intel needs `/dev/dri`; Apple is host-only. Before a second backend can be hub-started, factor a per-vendor launch spec (image, runtime, devices, env) keyed by vendor
- **Process attribution is uneven** - `processes[]` maps cleanly from `nvidia-smi --query-compute-apps`; `rocm-smi` and Intel expose this differently or not at all. The schema already degrades to `[]`, so this is acceptable, but the "attribute load to a user" feature will be NVIDIA-strong and best-effort elsewhere

Net: keep the schema, add `vendor` per GPU and an `api_version`, and concentrate the remaining work on a per-vendor launch spec plus optional multi-URL aggregation. The contract itself does not need a redesign.
