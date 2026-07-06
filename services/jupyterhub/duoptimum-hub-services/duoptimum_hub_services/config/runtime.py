"""Boot-time runtime assembly for the hub config (config simplification Batch 4).

`assemble_runtime(settings, compose_project)` runs the GPU-detection -> sidecar
lifecycle -> gpu-cache -> branding orchestration - the same calls, in the same order,
with the same side effects (starts the gpuinfo sidecar, registers the atexit cleanup,
copies branding assets) - and returns a frozen `Runtime` bundling the produced values.

This is a VERBATIM move of jupyterhub_config.py's Section-3 GPU/branding block: the
side-effect ordering invariant is preserved by construction (nothing is reordered).
The boot-level confirmation (that the sidecar starts, detection works, teardown fires)
rides the functional suite on a rebuilt image - it cannot run without Docker + a booted
hub, so this module is verified locally only for import-cleanliness and Runtime shape.
"""

import atexit
from dataclasses import dataclass

from .. import (
    NvidiaGpuProvider,
    configure_gpu_cache,
    ensure_gpuinfo_sidecar,
    gpu_summary_lines,
    is_wsl2,
    resolve_gpu_mode,
    resolve_gpu_vendor_provider,
    setup_branding,
    stop_gpuinfo_sidecar,
)
from ..docker_utils import resolve_gpuinfo_network
from ..logging_setup import log


@dataclass(frozen=True)
class Runtime:
    """Values discovered/produced at boot by assemble_runtime (GPU + branding)."""
    gpu_vendor: object            # vendor provider (device request + visibility env)
    gpuinfo_url: str              # sidecar base URL with {hostname} runtime-resolved ('' when down)
    gpuinfo_sidecar_up: bool
    gpu_enabled: int              # 0|1 - GPU on only when devices are actually detected
    nvidia_detected: int          # 0|1
    gpu_list: list                # list of GPU dicts
    gpu_uuid_by_index: dict       # index -> UUID for CUDA_VISIBLE_DEVICES
    gpu_isolation_enforced: bool  # real only on native Linux (WSL2 is advisory)
    branding: dict                # resolved logo/favicon/icon paths + URLs


def assemble_runtime(settings, compose_project):
    """Run the GPU/sidecar/branding orchestration once at boot and bundle the results.

    ``compose_project`` is the runtime-discovered hub compose project (not an env read),
    threaded in from the config; everything else comes off ``settings``.
    """
    # GPU vendor provider (NVIDIA reference today) - resolved once, threaded to the
    # per-user GPU policy + the sidecar launcher. Falls back to NVIDIA so resolution can
    # never return None and crash boot - the subsystem degrades, never dies.
    gpu_vendor = resolve_gpu_vendor_provider() or NvidiaGpuProvider()
    # Self-start the gpuinfo sidecar (best-effort) so detection talks to a reachable peer
    # instead of waiting on compose; returns its base URL with {hostname} filled from the
    # address discovered for the container it created - or '' when the sidecar isn't up.
    gpuinfo_url = (
        ensure_gpuinfo_sidecar(
            settings.gpuinfo_nvidia_image, resolve_gpuinfo_network(), settings.gpuinfo_nvidia_url,
            compose_project, container_name=settings.gpuinfo_nvidia_container_name,
            container_role_label_key=settings.label_container_role_key,
            container_role_label_value=settings.label_container_role_gpuinfo,
            container_description_label_key=settings.label_container_description,
            container_description="GPU-info sidecar - GPU detection, utilisation and per-GPU processes",
            gpu_runtime=gpu_vendor.runtime_name(),  # vendor's docker runtime; requested only if the host registers it
        )
        if settings.gpu_enabled != 0 else ""
    )
    gpuinfo_sidecar_up = bool(gpuinfo_url)
    # Point the detection client + utilisation sampler at the runtime-resolved URL.
    configure_gpu_cache(gpuinfo_url)
    # Tie the sidecar's lifecycle to the hub: remove it when the hub exits so it does not
    # linger as an orphan. Best-effort - skipped on a hard SIGKILL.
    if gpuinfo_sidecar_up:
        atexit.register(stop_gpuinfo_sidecar, gpuinfo_url, settings.gpuinfo_nvidia_container_name, compose_project)
    # probe only when the sidecar is actually up; otherwise skip straight to last-known/off
    # so a missing sidecar never stalls boot on DNS/connect
    gpu_enabled, nvidia_detected, gpu_list = resolve_gpu_mode(settings.gpu_enabled, probe_sidecar=gpuinfo_sidecar_up)
    if settings.gpu_enabled != 0 and not gpuinfo_sidecar_up:
        log.warning(
            "[GPU] gpuinfo-nvidia sidecar did not start -> GPU not detected (nvidia) -> "
            "GPU disabled; labs start CPU-only (see [GPUInfo] above for the cause)")
    # index -> UUID map for CUDA_VISIBLE_DEVICES (UUIDs stable across in-container GPU
    # re-indexing). isolation is real only on native Linux; on WSL2 it is advisory.
    gpu_uuid_by_index = {str(g.get('index')): g.get('uuid', '') for g in gpu_list if g.get('uuid')}
    gpu_isolation_enforced = bool(gpu_list) and not is_wsl2()
    log.info(
        f"[GPU] enabled={gpu_enabled} detected={nvidia_detected} "
        f"isolation_enforced={gpu_isolation_enforced} gpus={gpu_list}")
    if gpuinfo_sidecar_up:
        for _gpu_line in gpu_summary_lines():
            log.info(f"[GPU] {_gpu_line}")

    # Process branding URIs: file:// copies to the JupyterHub static dir, URLs pass through.
    branding = setup_branding(
        logo_uri=settings.branding_logo_uri,
        favicon_uri=settings.branding_favicon_uri,
        favicon_busy_uri=settings.branding_favicon_busy_uri,
        lab_main_icon_uri=settings.branding_lab_main_icon_uri,
        lab_splash_icon_uri=settings.branding_lab_splash_icon_uri,
        stage=settings.branding_stage,
    )

    return Runtime(
        gpu_vendor=gpu_vendor,
        gpuinfo_url=gpuinfo_url,
        gpuinfo_sidecar_up=gpuinfo_sidecar_up,
        gpu_enabled=gpu_enabled,
        nvidia_detected=nvidia_detected,
        gpu_list=gpu_list,
        gpu_uuid_by_index=gpu_uuid_by_index,
        gpu_isolation_enforced=gpu_isolation_enforced,
        branding=branding,
    )
