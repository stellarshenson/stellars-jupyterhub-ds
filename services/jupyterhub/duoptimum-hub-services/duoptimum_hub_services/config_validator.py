"""Central hub-config validation: conf gathers raw env-derived values, hands them here,
this decides pass/fail.

Why centralised: keeps config/jupyterhub_config.py thin - no scattered `if not X: raise`
blocks. Defaults live in the Dockerfile ENV (the image is the source of defaults), so conf
reads required vars RAW (no inline Python fallback). A missing required var here means the
hub was run outside its image without supplying it - fail hard with one aggregated message
naming every offender, rather than booting half-configured.

Two severities:
  - errors   -> hub must NOT start (missing required var, or cross-value inconsistency)
  - warnings -> hub starts degraded, operator should know (configured-but-broken value)

Namespace: every label-based UNIQUENESS check is scoped to the current namespace (= the
compose project, com.docker.compose.project / JUPYTERHUB_COMPOSE_PROJECT_NAME). Many
deployments share one docker host; each owns its own role-labelled hub_shared / hub_docker /
networks, so "exactly one resource holds role X" means one within THIS project. The runtime
resolvers (resolve_self_*_by_label) are namespace-safe by construction - they inspect only
what the hub itself mounts / is attached to - so the duplicate-role check they raise already
counts per-namespace. This module is pure (dict in, result out) and adds no host-wide scan.
"""

import os

# (key, human label) - required non-empty; baked as Dockerfile ENV. Empty => run outside image.
_REQUIRED = [
    ("admin", "JUPYTERHUB_ADMIN_USERNAME (admin username)"),
    ("lab_image", "JUPYTERHUB_LAB_IMAGE (lab image to spawn)"),
    ("namespace", "namespace (compose project) - discovered from the hub's own com.docker.compose.project label; run the hub under docker compose"),
    ("lab_network_name", "JUPYTERHUB_NETWORK_NAME (hub<->lab network)"),
    ("network_role_label_key", "JUPYTERHUB_LABEL_NETWORK_ROLE_KEY"),
    ("volume_role_label_key", "JUPYTERHUB_LABEL_VOLUME_ROLE_KEY"),
    ("container_role_label_key", "JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY"),
    ("lab_network_role_label", "JUPYTERHUB_LABEL_NETWORK_ROLE_LAB"),
    ("gpuinfo_network_role_label", "JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO"),
    ("shared_volume_role_label", "JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED"),
    ("docker_proxy_volume_role_label", "JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY"),
    ("gpuinfo_container_role_label", "JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO"),
    ("lab_container_role_label", "JUPYTERHUB_LABEL_CONTAINER_ROLE_LAB (spawned-lab container role)"),
    ("volume_description_label_key", "JUPYTERHUB_LABEL_VOLUME_DESCRIPTION"),
    ("volume_owner_label_key", "JUPYTERHUB_LABEL_VOLUME_OWNER_KEY"),
    ("container_description_label_key", "JUPYTERHUB_LABEL_CONTAINER_DESCRIPTION"),
    ("docker_proxy_owner_label_key", "JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_KEY"),
    ("docker_proxy_owner_label_value", "JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_VALUE"),
    ("lab_container_name_template", "JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE"),
    ("gpuinfo_nvidia_image", "JUPYTERHUB_GPUINFO_NVIDIA_IMAGE"),
    ("gpuinfo_nvidia_container_name", "JUPYTERHUB_GPUINFO_NVIDIA_CONTAINER_NAME"),
    ("gpuinfo_nvidia_url", "JUPYTERHUB_GPUINFO_NVIDIA_URL"),
    ("docker_proxy_socket_dir", "JUPYTERHUB_DOCKER_PROXY_SOCKET_DIR"),
    ("docker_proxy_sockets_volume", "JUPYTERHUB_DOCKER_PROXY_SOCKETS_VOLUME (resolved volume)"),
    ("user_compose_project_template", "JUPYTERHUB_DOCKER_PROXY_USER_COMPOSE_PROJECT_TEMPLATE"),
]

# branding icon URIs - optional; file:// must point at an existing file (else warn, stock used)
_BRANDING_URIS = [
    ("branding_logo_uri", "JUPYTERHUB_BRANDING_LOGO_URI (hub logo)"),
    ("branding_favicon_uri", "JUPYTERHUB_BRANDING_FAVICON_URI (favicon)"),
    ("branding_favicon_busy_uri", "JUPYTERHUB_BRANDING_FAVICON_BUSY_URI (busy favicon)"),
    ("branding_lab_main_icon_uri", "JUPYTERHUB_BRANDING_LAB_MAIN_ICON_URI (lab main icon)"),
    ("branding_lab_splash_uri", "JUPYTERHUB_BRANDING_LAB_SPLASH_ICON_URI (lab splash icon)"),
]


class ValidationResult:
    """Outcome of validate_hub_config: collected errors + warnings, no side effects."""

    def __init__(self, errors=None, warnings=None):
        self.errors = list(errors or [])
        self.warnings = list(warnings or [])

    @property
    def ok(self):
        return not self.errors

    def raise_if_errors(self, log=None):
        """Log every warning (if a logger given), then SystemExit on any error - one message
        listing all offenders so the operator fixes them in a single pass, not one boot each."""
        if log is not None:
            # pre-format so the call is logger-agnostic: stdlib (%-style) and loguru
            # ({}-style) both accept a fully-rendered single string with no args
            for w in self.warnings:
                log.warning(f"[config] {w}")
        if self.errors:
            raise SystemExit(
                "Hub configuration invalid - refusing to start:\n  - "
                + "\n  - ".join(self.errors)
            )


def _missing(value):
    """True when a required value is absent/blank (None, '', or whitespace)."""
    return value is None or (isinstance(value, str) and not value.strip())


def _branding_file_missing(uri, path_exists):
    """A file:// branding URI whose target file does not exist (http(s)/empty -> False)."""
    if not uri or not uri.startswith("file://"):
        return False
    return not path_exists(uri[len("file://"):])


def validate_hub_config(values, *, path_exists=os.path.exists):
    """Validate gathered hub config. Pure: dict in, ValidationResult out (no env/docker reads).

    values: required keys per _REQUIRED, optional branding/gpuinfo/shared keys. path_exists is
    injectable for tests. Errors = missing required + inconsistency; warnings = degraded config.
    """
    errors = []
    warnings = []

    for key, label in _REQUIRED:
        if _missing(values.get(key)):
            errors.append(f"{label} is required but unset (baked as a Dockerfile ENV - run via the image or set it)")

    # consistency: the two network roles share one label key; equal values are indistinguishable
    lab_role = (values.get("lab_network_role_label") or "").strip()
    gpuinfo_role = (values.get("gpuinfo_network_role_label") or "").strip()
    if lab_role and gpuinfo_role and lab_role == gpuinfo_role:
        errors.append(
            "JUPYTERHUB_LABEL_NETWORK_ROLE_LAB and JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO are both "
            f"'{lab_role}' - the lab and gpuinfo networks would be indistinguishable on key "
            f"'{values.get('network_role_label_key')}'; give them distinct role values"
        )

    # consistency: shared + docker-proxy volume roles share one label key; equal values would
    # resolve to the SAME volume (or raise on >1) - the symmetric case to the network roles
    shared_vrole = (values.get("shared_volume_role_label") or "").strip()
    dp_vrole = (values.get("docker_proxy_volume_role_label") or "").strip()
    if shared_vrole and dp_vrole and shared_vrole == dp_vrole:
        errors.append(
            "JUPYTERHUB_LABEL_VOLUME_ROLE_SHARED and JUPYTERHUB_LABEL_VOLUME_ROLE_DOCKER_PROXY are both "
            f"'{shared_vrole}' - the shared and docker-proxy volumes would be indistinguishable on key "
            f"'{values.get('volume_role_label_key')}'; give them distinct role values"
        )

    # consistency: per-user templates MUST carry {username} or every user collides on one name
    name_tmpl = values.get("lab_container_name_template")
    if name_tmpl and "{username}" not in name_tmpl:
        errors.append(
            f"JUPYTERHUB_LAB_CONTAINER_NAME_TEMPLATE ('{name_tmpl}') must contain '{{username}}' - "
            "without it every user's lab container would collide on one name"
        )
    proj_tmpl = values.get("user_compose_project_template")
    if proj_tmpl and "{username}" not in proj_tmpl:
        errors.append(
            f"JUPYTERHUB_DOCKER_PROXY_USER_COMPOSE_PROJECT_TEMPLATE ('{proj_tmpl}') must contain "
            "'{username}' - per-user docker compose projects would otherwise collide"
        )
    # consistency: the proxy owner VALUE is a per-user template; without {username} every user's
    # proxy-created resources would carry one shared owner value (ownership filtering collapses)
    dp_owner_val = values.get("docker_proxy_owner_label_value")
    if dp_owner_val and "{username}" not in dp_owner_val:
        errors.append(
            f"JUPYTERHUB_LABEL_DOCKER_PROXY_OWNER_VALUE ('{dp_owner_val}') must contain '{{username}}' - "
            "without it every user's proxy-created resources would carry the same owner value"
        )

    # warnings: degraded-but-bootable - features silently off unless the operator is told
    if _missing(values.get("gpuinfo_network_name")):
        warnings.append(
            "gpuinfo network could not be resolved by role "
            f"'{values.get('network_role_label_key')}={gpuinfo_role}' in this namespace - the GPU "
            "sidecar is unplaceable, GPU features are OFF"
        )
    if _missing(values.get("shared_volume_name")):
        warnings.append(
            "shared volume could not be resolved by role "
            f"'{values.get('volume_role_label_key')}={(values.get('shared_volume_role_label') or '').strip()}' "
            "in this namespace - the one-click /mnt/shared quick-add is hidden (manual mounts still work)"
        )
    for key, label in _BRANDING_URIS:
        if _branding_file_missing(values.get(key), path_exists):
            warnings.append(f"{label} points at a file:// path that does not exist - falling back to the stock asset")

    return ValidationResult(errors, warnings)
