"""NVIDIA GPU auto-detection."""


def detect_nvidia(nvidia_autodetect_image='nvidia/cuda:13.0.2-base-ubuntu24.04'):
    """Return 1 if the host exposes any NVIDIA GPU, else 0.

    The hub container has no GPU access of its own, so presence is probed by
    running nvidia-smi in an ephemeral CUDA container (runtime=nvidia). Derived
    from enumerate_gpus() so detection and enumeration share one container run.
    """
    return 1 if enumerate_gpus(nvidia_autodetect_image) else 0


def enumerate_gpus(nvidia_autodetect_image='nvidia/cuda:13.0.2-base-ubuntu24.04'):
    """List the host's NVIDIA GPUs by running nvidia-smi in a CUDA container.

    Mirrors detect_nvidia()'s throwaway-container pattern. Returns a list of
    dicts ``{index, name, uuid, memory_mb}`` (index/name/uuid as strings,
    memory_mb as int), or ``[]`` on any failure (no GPU, no nvidia runtime,
    docker error) so callers never crash.
    """
    import docker

    gpus = []
    client = None
    try:
        client = docker.DockerClient('unix://var/run/docker.sock')
        output = client.containers.run(
            image=nvidia_autodetect_image,
            command=(
                'nvidia-smi '
                '--query-gpu=index,name,uuid,memory.total '
                '--format=csv,noheader'
            ),
            runtime='nvidia',
            name='jupyterhub_gpu_enumerate',
            stderr=False,
            stdout=True,
        )
        for line in output.decode('utf-8', 'replace').strip().splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 4:
                continue
            mem = parts[3].split()[0] if parts[3] else '0'  # "81920 MiB" -> "81920"
            try:
                mem_mb = int(mem)
            except ValueError:
                mem_mb = 0
            gpus.append({
                'index': parts[0],
                'name': parts[1],
                'uuid': parts[2],
                'memory_mb': mem_mb,
            })
    except Exception:
        gpus = []
    if client is not None:
        try:
            client.containers.get('jupyterhub_gpu_enumerate').remove(force=True)
        except Exception:
            pass
    return gpus


def resolve_gpu_mode(gpu_enabled, nvidia_image):
    """Resolve GPU mode from env setting. Returns (gpu_enabled, nvidia_detected, gpu_list).

    gpu_enabled: 0=disabled, 1=enabled, 2=autodetect

    Whenever GPU is on - forced (mode 1) or autodetected (mode 2) - a single
    ephemeral CUDA container enumerates the host GPUs (the hub itself has no GPU
    access). In autodetect, presence is derived from the enumeration so the mode
    collapses to on/off. In forced mode the grant stays on regardless of what the
    enumeration finds; the list is still populated for the UI. Mode 0 never spins
    the container.
    """
    nvidia_detected = 0
    gpu_list = []
    if gpu_enabled in (1, 2):
        gpu_list = enumerate_gpus(nvidia_image)
        nvidia_detected = 1 if gpu_list else 0
        if gpu_enabled == 2:
            gpu_enabled = 1 if nvidia_detected else 0
    return gpu_enabled, nvidia_detected, gpu_list
