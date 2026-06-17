"""JupyterHub background service definitions (activity sampler, idle culler)."""

import sys


def get_services_and_roles(sample_interval):
    """Build services and roles lists. Returns (services, roles).

    Args:
        sample_interval: activity sampling interval in seconds

    Activity Sampler is always enabled. Idle culling is handled in-process by
    `optimum_hub_services.idle_culler.schedule_idle_culler` (not a managed service), so
    per-user session extensions are honoured - the external jupyterhub-idle-culler
    cannot read spawner state.
    """
    services = []
    roles = []

    # Activity Sampler Service (always enabled)
    roles.append({
        "name": "activity-sampler-role",
        "scopes": ["list:users", "read:users:activity", "read:servers"],
        "services": ["activity-sampler"],
    })
    services.append({
        "name": "activity-sampler",
        "command": [sys.executable, "-m", "optimum_hub_services.activity.service"],
    })
    print(f"[Activity Sampler] Enabled - interval={sample_interval}s")

    return services, roles
