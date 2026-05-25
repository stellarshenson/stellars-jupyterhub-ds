# GPU Detection and Configuration

The platform detects host GPUs, enumerates them, and lets administrators grant GPU access per group - either all GPUs or a specific subset. The JupyterHub container itself runs without GPU access; GPUs are attached only to spawned user containers at launch time.

## How detection works

The hub has no GPU of its own, so it cannot read `nvidia-smi` directly. Instead it asks Docker to run a short-lived CUDA container with the NVIDIA runtime and parses that container's output. The same single run both detects presence and enumerates the devices, so no second container is ever spawned.

- Detection runs once at hub startup, in `resolve_gpu_mode()` (`stellars_hub/gpu.py`)
- The ephemeral container runs `nvidia-smi --query-gpu=index,name,uuid,memory.total --format=csv,noheader`
- Its stdout is parsed into a list of `{index, name, uuid, memory_mb}` by `enumerate_gpus()`
- The enumerated list is cached and passed to the Groups admin page; any failure (no GPU, no NVIDIA runtime, Docker error) yields an empty list rather than an error

`JUPYTERHUB_GPU_ENABLED` controls the mode and `JUPYTERHUB_NVIDIA_IMAGE` selects the CUDA image used for the probe:

- `0` disabled - no container is spawned, no GPUs enumerated
- `1` forced on - GPUs are still enumerated (for the UI and logs), and the grant stays on regardless of what is found
- `2` autodetect (default) - GPUs are enumerated and access collapses to on/off based on whether any were found

The startup log prints a single line, for example `[GPU debug] enabled=1 detected=1 gpus=[{'index': '0', 'name': 'NVIDIA ...', 'memory_mb': 81920}]`.

## Per-group GPU access

The Groups admin page (`/hub/groups`) exposes a GPU section per group:

- **Enable GPU access** - grants GPU to members of the group
- **All GPUs** - default; passes every GPU to the user container
- **Specific GPUs** - deselect "All GPUs" to reveal per-GPU checkboxes (index, name, memory) and choose a subset

If the host reports no GPUs, the whole section is grayed out and a "No GPUs detected on this host" note is shown - the options cannot be enabled and are ignored at spawn, so launching containers never fails on a GPU-less host.

### Validation

Enabling GPU access while deselecting "All GPUs" requires at least one specific GPU. Saving with access on, "All GPUs" off, and nothing selected is rejected both in the browser and on the server with the message: `Select at least one GPU, or enable "All GPUs".` The check is `validate_gpu_selection()` in `stellars_hub/groups_config.py`.

## Resolution across multiple groups

A user can belong to several groups. Their effective GPU access is collapsed by `resolve_group_config()` (`stellars_hub/group_resolver.py`):

- **Access** is OR-ed across groups, then gated on hardware availability - if no GPU is present, access resolves to off
- **All GPUs wins** - if any granting group selects all, the user gets all GPUs
- **Specific GPUs union** - otherwise the selected device indices from all granting groups are combined
- **Defensive fallback** - a grant with neither "all" nor any specific GPU resolves to all (the save-time validator already prevents this state)

## Application at spawn

The pre-spawn hook (`stellars_hub/hooks.py`) translates the resolved selection into a Docker device request on the user container:

- All GPUs - `{'Driver': 'nvidia', 'Count': -1, 'Capabilities': [['gpu']]}`
- Specific GPUs - `{'Driver': 'nvidia', 'DeviceIDs': ['0', '2'], 'Capabilities': [['gpu']]}`

Because access is already gated on hardware availability, a GPU-less host skips this entirely and sets no device request - spawns proceed normally. When GPU is granted, the container also receives `ENABLE_GPU_SUPPORT=1` and `ENABLE_GPUSTAT=1`. The spawn log records the selection, for example `gpu=True gpu_sel=['0', '2']`.

## Configuration reference

- `JUPYTERHUB_GPU_ENABLED`: `0` disabled, `1` forced on, `2` autodetect (default)
- `JUPYTERHUB_NVIDIA_IMAGE`: CUDA image for the detection/enumeration probe (default `nvidia/cuda:13.0.2-base-ubuntu24.04`)

Group GPU settings persist in the group configuration store (`stellars_hub/groups_config.py`): `gpu_access` (bool), `gpu_all` (bool, default true), and `gpu_device_ids` (list of index strings). They take effect on each user's next spawn.

## Troubleshooting

- **No GPUs listed but the host has them**: confirm the NVIDIA Container Toolkit is installed and `docker run --rm --gpus all <nvidia_image> nvidia-smi` works from the host; verify `JUPYTERHUB_NVIDIA_IMAGE` matches your driver's CUDA version
- **GPU section grayed out**: the startup probe found no GPUs (mode `0`, no NVIDIA runtime, or a failed probe) - check the `[GPU debug]` startup log line
- **Specific GPU not honored**: selections are applied on the next spawn; restart the user server after changing the group configuration
