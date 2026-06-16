# gpuinfo-nvidia

NVIDIA implementation of the Stellars GPU-info sidecar API. A long-running peer the JupyterHub hub queries over a dedicated network instead of spawning an ephemeral CUDA container on every probe.

## Why

The hub container has no GPU access of its own. The previous approach ran `nvidia-smi` inside a throwaway `nvidia/cuda` container for both startup detection and periodic utilisation sampling - a ~1-3s container spin every cycle. This sidecar runs `nvidia-smi` in a single warm process and answers over HTTP in milliseconds.

## Vendor-neutral contract

The HTTP API is shared across backends. This package is the NVIDIA backend; future `gpuinfo-amd`, `gpuinfo-intel`, `gpuinfo-applesilicon` peers implement the same schema, so the hub stays vendor-agnostic. Fields a backend cannot report are returned `null`, never omitted.

- `GET /health` -> `{status, vendor, driver_available}` - always 200 while the process is up, so the hub's health-gated dependency is satisfied even on GPU-less hosts
- `GET /gpus` -> `{vendor, available, count, gpus[], timestamp}`

Each entry in `gpus[]`:

- `index`, `name`, `uuid`
- `utilization` (percent), `memory_used_mb`, `memory_total_mb`
- `processes[]` - `{pid, name, used_memory_mb}` for compute processes holding the GPU (the hook for attributing load to a user)

## Run

```bash
# local (needs nvidia-smi on PATH; returns available:false otherwise)
python -m gpuinfo_nvidia            # serves on 0.0.0.0:8000

# container (needs the nvidia container runtime)
docker run --rm --runtime=nvidia -p 8000:8000 stellars/stellars-gpuinfo-nvidia:latest
```

Environment: `GPUINFO_HOST` (default `0.0.0.0`), `GPUINFO_PORT` (default `8000`), `GPUINFO_LOG_LEVEL` (default `warning`).

## Develop

```bash
make install   # editable install with test extras
make test      # pytest (subprocess mocked - no GPU required)
make image     # build the sidecar image (build context = repo root)
```
