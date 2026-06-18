"""GPU auto-detection: assert JupyterHub correctly detects and configures GPU
support when a GPU is present.

Reads the hub's startup `[GPU debug] enabled=N detected=N ... gpus=[...]` line
(no spawn needed). Skips when no GPU is detected, so it is a no-op on a CPU-only
host. To exercise auto-detection, run on a GPU host with:

    FUNCTEST_GPU_ENABLED=2 make test-functional
"""

import os
import re
from urllib.parse import urlparse

import pytest

# Derive the hub container name from the same BASE_URL host the rest of the
# harness uses (compose names it stellars-functest-<service>), so a service
# rename can't strand a hardcoded name here again.
HUB_CONTAINER = f"stellars-functest-{urlparse(os.environ.get('BASE_URL', 'http://duoptimum-hub:8000/jupyterhub')).hostname or 'duoptimum-hub'}"


@pytest.mark.gpu
@pytest.mark.acc_crit("functional-test-harness::Auto-detect enables on GPU host")
def test_gpu_autodetection(docker_client):
    logs = docker_client.containers.get(HUB_CONTAINER).logs().decode("utf-8", "replace")
    m = re.search(r"\[GPU debug\] enabled=(\d) detected=(\d).*?gpus=(\[.*?\])", logs, re.S)
    assert m, "hub did not log the GPU detection line"
    enabled, detected, gpus = int(m.group(1)), int(m.group(2)), m.group(3)

    if not detected:
        pytest.skip("no GPU detected on host (FUNCTEST_GPU_ENABLED=2 make test-functional on a GPU host)")

    # GPU present -> auto-detection must have enabled GPU support and enumerated GPUs.
    assert enabled == 1, "GPU detected but support not enabled by auto-detection"
    assert gpus != "[]", "GPU detected but no GPUs enumerated"
