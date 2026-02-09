"""JupyterHub background service definitions (activity sampler, idle culler)."""

import sys


def get_services_and_roles(culler_enabled, culler_timeout, culler_interval, culler_max_age, sample_interval):
    """Build services and roles lists. Returns (services, roles).

    Args:
        culler_enabled: 0 or 1 - whether idle culler is active
        culler_timeout: idle timeout in seconds
        culler_interval: cull check interval in seconds
        culler_max_age: max server age in seconds (0 = disabled)
        sample_interval: activity sampling interval in seconds

    Activity Sampler is always enabled.
    Idle Culler is conditionally enabled based on culler_enabled.
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
        "command": [sys.executable, "-m", "stellars_hub.activity.service"],
    })
    print(f"[Activity Sampler] Enabled - interval={sample_interval}s")

    # Idle Culler Service (optional)
    if culler_enabled == 1:
        roles.append({
            "name": "jupyterhub-idle-culler-role",
            "scopes": ["list:users", "read:users:activity", "read:servers", "delete:servers"],
            "services": ["jupyterhub-idle-culler"],
        })

        culler_cmd = [
            sys.executable,
            "-m", "jupyterhub_idle_culler",
            f"--timeout={culler_timeout}",
            f"--cull-every={culler_interval}",
        ]
        if culler_max_age > 0:
            culler_cmd.append(f"--max-age={culler_max_age}")

        services.append({
            "name": "jupyterhub-idle-culler",
            "command": culler_cmd,
        })

        print(
            f"[Idle Culler] Enabled - timeout={culler_timeout}s, "
            f"interval={culler_interval}s, max_age={culler_max_age}s"
        )

    return services, roles
