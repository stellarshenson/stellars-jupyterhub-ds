"""NVIDIA GPU auto-detection."""


def detect_nvidia(nvidia_autodetect_image='nvidia/cuda:13.0.2-base-ubuntu24.04'):
    """Run docker image with nvidia driver and execute nvidia-smi to verify GPU."""
    import docker
    client = docker.DockerClient('unix://var/run/docker.sock')
    result = 0
    try:
        client.containers.run(
            image=nvidia_autodetect_image,
            command='nvidia-smi',
            runtime='nvidia',
            name='jupyterhub_nvidia_autodetect',
            stderr=True,
            stdout=True,
        )
        result = 1
    except Exception:
        result = 0
    try:
        client.containers.get('jupyterhub_nvidia_autodetect').remove(force=True)
    except Exception:
        pass
    return result


def resolve_gpu_mode(gpu_enabled, nvidia_image):
    """Resolve GPU mode from env setting. Returns (gpu_enabled, nvidia_detected).

    gpu_enabled: 0=disabled, 1=enabled, 2=autodetect
    """
    nvidia_detected = 0
    if gpu_enabled == 2:
        nvidia_detected = detect_nvidia(nvidia_image)
        gpu_enabled = 1 if nvidia_detected else 0
    return gpu_enabled, nvidia_detected
