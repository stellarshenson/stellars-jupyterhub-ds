# GPU Selection for JupyterLab Containers

## What the platform applies (per user, `hooks.py`)

- device request: all -> `{'Driver':'nvidia','Count':-1,'Capabilities':[['gpu']]}`; specific -> `{'Driver':'nvidia','DeviceIDs':['0','2'],...}`
- `NVIDIA_VISIBLE_DEVICES`: `all` / `0,2` / `void` (no access)
- `ENABLE_GPU_SUPPORT`, `ENABLE_GPUSTAT`

No `/dev/dxg` or wsl mounts in config; the device request triggers the NVIDIA runtime. `NVIDIA_VISIBLE_DEVICES` is set explicitly: the toolkit treats it as authoritative and the jupyterlab image bakes `=all`.

## Host models

- native Linux: per-GPU `/dev/nvidiaN` nodes; toolkit injects only allowed nodes, cgroup denies the rest
- WSL2 / Docker Desktop: no per-GPU nodes, single `/dev/dxg`; any GPU-enabled container sees all GPUs

## Measured (WSL2 host, 3 GPUs)

- device request `DeviceIDs:["2"]` set correctly; `nvidia-smi -L` showed all 3
- container had no `/dev/nvidia*`, only `/dev/dxg`
- `NVIDIA_VISIBLE_DEVICES=<single-UUID>` -> all 3
- `--gpus "device=2"` -> `NVIDIA_VISIBLE_DEVICES=2` in container -> all 3

## Enforcement

- native Linux: specific selection enforced (container sees only selected GPUs)
- WSL2 / Docker Desktop: specific selection not enforced (container sees all GPUs)
- `CUDA_VISIBLE_DEVICES`: honored by CUDA apps only, ignored by `nvidia-smi`, user-overridable, not set by the platform

Related: `docs/gpu-detection-and-configuration.md`
