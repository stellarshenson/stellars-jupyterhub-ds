# GPU Selection for JupyterLab Containers

## What the platform applies (per user, `hooks.py`)

- device request: all -> `{'Driver':'nvidia','Count':-1,'Capabilities':[['gpu']]}`; specific -> `{'Driver':'nvidia','DeviceIDs':['0','2'],...}`
- `NVIDIA_VISIBLE_DEVICES`: `all` / `0,2` (host indices) / `void` (no access)
- `CUDA_VISIBLE_DEVICES`: set to the selected GPU **UUIDs** for a specific selection; unset for all/no-access
- `ENABLE_GPU_SUPPORT`, `ENABLE_GPUSTAT`

No `/dev/dxg` or wsl mounts in config; the device request triggers the NVIDIA runtime. `NVIDIA_VISIBLE_DEVICES` is set explicitly: the toolkit treats it as authoritative and the jupyterlab image bakes `=all`. `CUDA_VISIBLE_DEVICES` uses UUIDs (not indices) because a selected GPU re-indexes to 0 inside the container on native Linux, and UUIDs are order-independent.

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
- WSL2 / Docker Desktop: specific selection not enforced (container sees all GPUs); confirmed unresolved upstream ([nvidia-container-toolkit #983](https://github.com/NVIDIA/nvidia-container-toolkit/issues/983))
- `CUDA_VISIBLE_DEVICES` (UUID, set by the platform for specific selections): CUDA apps default to the selected GPUs on both platforms; `nvidia-smi`/gpustat ignore it and a user can override it -> soft, not isolation

## WSL2 advisory

WSL2 is detected at startup (`is_wsl2()`, kernel string) -> `gpu_isolation_enforced=False`. The Groups config screen then shows an "advisory, not a hard limit" warning in the GPU section. On native Linux the flag is True and no warning is shown.

Related: `docs/gpu-detection-and-configuration.md`
