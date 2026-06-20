"""Build/config invariant: compose label literals MUST match the baked Dockerfile env defaults.

Hub discovers nets by role + stamps a container role label; compose stamps the same literals
on the nets + the gpuinfo service. Two sources, silent drift risk - this turns the `MUST match`
comments into an enforced invariant. Skips when the repo root files are absent (packaged run).
"""

import re
from pathlib import Path

import pytest

def _find_repo_root():
    # walk up to the dir holding both compose.yml and the hub Dockerfile; a fixed
    # parents[N] crashed in the packaged /src/... layout where the depth differs
    for p in Path(__file__).resolve().parents:
        if (p / "compose.yml").is_file() and (p / "services" / "jupyterhub" / "Dockerfile.jupyterhub").is_file():
            return p
    return None


_ROOT = _find_repo_root()
_COMPOSE = _ROOT / "compose.yml" if _ROOT else None
_DOCKERFILE = _ROOT / "services" / "jupyterhub" / "Dockerfile.jupyterhub" if _ROOT else None

pytestmark = pytest.mark.skipif(
    _ROOT is None,
    reason="repo root compose.yml / Dockerfile not available (packaged test run)",
)


def _env(name):
    """Value baked by `ENV <name>=<value>` in the hub Dockerfile."""
    m = re.search(rf"^ENV {re.escape(name)}=(.*)$", _DOCKERFILE.read_text(), re.M)
    return m.group(1).strip() if m else None


def _compose_label_values(key):
    """Every value stamped for label `key` in compose.yml (map style: `key: "value"`)."""
    return re.findall(
        rf'^\s*{re.escape(key)}:\s*"?([^"\n#]+?)"?\s*(?:#.*)?$',
        _COMPOSE.read_text(), re.M,
    )


def test_network_role_labels_match_baked_env():
    key = _env("JUPYTERHUB_LABEL_NETWORK_ROLE_KEY")
    assert key == "hub.network.role"
    values = _compose_label_values(key)
    assert _env("JUPYTERHUB_LABEL_NETWORK_ROLE_LAB") in values, "compose must stamp the lab role"
    assert _env("JUPYTERHUB_LABEL_NETWORK_ROLE_GPUINFO") in values, "compose must stamp the gpuinfo role"


def test_container_role_label_matches_baked_env():
    key = _env("JUPYTERHUB_LABEL_CONTAINER_ROLE_KEY")
    assert key == "hub.container.role"
    assert _env("JUPYTERHUB_LABEL_CONTAINER_ROLE_GPUINFO") in _compose_label_values(key), \
        "compose gpuinfo service must stamp the container role"


def test_network_name_envs_baked_as_token():
    # the network-name env vars default to the {network} token (resolved per-context at boot)
    assert _env("JUPYTERHUB_NETWORK_NAME") == "{network}"
    assert _env("JUPYTERHUB_GPUINFO_NETWORK_NAME") == "{network}"
