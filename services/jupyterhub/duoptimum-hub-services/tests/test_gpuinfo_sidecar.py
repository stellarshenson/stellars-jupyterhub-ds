"""ensure_gpuinfo_sidecar() + _sidecar_host() - the hub-managed sidecar lifecycle and
the RUNTIME host discovery that fills the {hostname} placeholder.

The host is never hardcoded: after the hub creates the sidecar it reads the container's
address (its IP on the dedicated network) from the live container and substitutes it
into the URL template. These tests stub the docker SDK so no daemon is touched, and
assert the function returns the {hostname}-resolved URL on success and '' on every
degrade path (docker down, image absent, no name, undiscoverable address).
"""

import sys
from types import SimpleNamespace

from duoptimum_hub_services.gpuinfo_sidecar import (
    _compose_container_name,
    _sidecar_host,
    ensure_gpuinfo_sidecar,
    stop_gpuinfo_sidecar,
)


# ── _sidecar_host: read the address from the LIVE container ───────────────────

class _Container:
    def __init__(self, *, name="gpuinfo-nvidia", networks=None, reload_raises=False, name_raises=False):
        self._name = name
        self._networks = networks or {}
        self._reload_raises = reload_raises
        self._name_raises = name_raises

    def reload(self):
        if self._reload_raises:
            raise RuntimeError("docker reload failed")

    @property
    def attrs(self):
        return {"NetworkSettings": {"Networks": self._networks}}

    @property
    def name(self):
        if self._name_raises:
            raise RuntimeError("no name")
        return self._name


def test_sidecar_host_prefers_network_ip():
    c = _Container(networks={"gpuinfo-net": {"IPAddress": "172.20.0.5"}})
    assert _sidecar_host(c, "gpuinfo-net") == "172.20.0.5"


def test_sidecar_host_falls_back_to_container_name_when_no_ip():
    # network attached but no IP populated yet -> the DNS-resolvable container name
    c = _Container(name="gpuinfo-nvidia", networks={"gpuinfo-net": {"IPAddress": ""}})
    assert _sidecar_host(c, "gpuinfo-net") == "gpuinfo-nvidia"


def test_sidecar_host_falls_back_when_network_absent():
    c = _Container(name="gpuinfo-nvidia", networks={"some-other-net": {"IPAddress": "10.0.0.9"}})
    assert _sidecar_host(c, "gpuinfo-net") == "gpuinfo-nvidia"


def test_sidecar_host_uses_name_when_reload_raises():
    c = _Container(name="gpuinfo-nvidia", reload_raises=True)
    assert _sidecar_host(c, "gpuinfo-net") == "gpuinfo-nvidia"


def test_sidecar_host_none_when_nothing_readable():
    c = _Container(reload_raises=True, name_raises=True)
    assert _sidecar_host(c, "gpuinfo-net") is None


# ── ensure_gpuinfo_sidecar: returns the {hostname}-resolved URL ───────────────

class _NotFound(Exception):
    pass


class _ImageNotFound(Exception):
    pass


class _FakeNetwork:
    def __init__(self, name):
        self.name = name

    def connect(self, container):
        pass


class _FakeContainers:
    """containers.get always 404s (no pre-existing sidecar, no hub match); run returns
    the configured container."""

    def __init__(self, run_container):
        self._run_container = run_container
        self.last_run_kwargs = None

    def get(self, name):
        raise _NotFound(name)

    def list(self):
        return []

    def run(self, **kwargs):
        self.last_run_kwargs = kwargs
        return self._run_container


class _FakeNetworks:
    """Compose OWNS the hub<->sidecar network, so get() returns it; the hub must NEVER
    create it (that historically clashed with compose's ownership check) - create() trips."""

    def __init__(self, *, present=True):
        self._present = present

    def get(self, name):
        if not self._present:
            raise _NotFound(name)
        return _FakeNetwork(name)

    def create(self, name, **kwargs):
        raise AssertionError("ensure_gpuinfo_sidecar must NOT create the network (compose owns it)")


class _FakeClient:
    def __init__(self, *, run_container, image_present=True, network_present=True, runtimes=None):
        self.containers = _FakeContainers(run_container)
        self.networks = _FakeNetworks(present=network_present)
        self._image_present = image_present
        self._runtimes = runtimes or {}  # registered docker runtimes; default none (CPU host / mock)

    @property
    def images(self):
        present = self._image_present

        class _Images:
            def get(self, image):
                if not present:
                    raise _ImageNotFound(image)
                return object()
        return _Images()

    def info(self):
        return {"Runtimes": dict(self._runtimes)}

    def close(self):
        pass


def _install_fake_docker(monkeypatch, *, client=None, client_raises=False):
    def DockerClient(*a, **k):
        if client_raises:
            raise RuntimeError("docker unavailable")
        return client
    fake = SimpleNamespace(
        DockerClient=DockerClient,
        errors=SimpleNamespace(NotFound=_NotFound, ImageNotFound=_ImageNotFound),
    )
    monkeypatch.setitem(sys.modules, "docker", fake)


def test_ensure_returns_url_with_discovered_ip(monkeypatch):
    container = _Container(name="gpuinfo-nvidia", networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    _install_fake_docker(monkeypatch, client=_FakeClient(run_container=container))
    out = ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        container_name="gpuinfo-nvidia",
    )
    assert out == "http://172.20.0.7:8000"


def test_ensure_falls_back_to_container_name_when_no_ip(monkeypatch):
    container = _Container(name="gpuinfo-nvidia", networks={})
    _install_fake_docker(monkeypatch, client=_FakeClient(run_container=container))
    out = ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        container_name="gpuinfo-nvidia",
    )
    assert out == "http://gpuinfo-nvidia:8000"


def test_ensure_empty_when_image_absent(monkeypatch):
    container = _Container(networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    _install_fake_docker(monkeypatch, client=_FakeClient(run_container=container, image_present=False))
    out = ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        container_name="gpuinfo-nvidia",
    )
    assert out == ""


def test_ensure_empty_when_docker_unavailable(monkeypatch):
    _install_fake_docker(monkeypatch, client_raises=True)
    out = ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        container_name="gpuinfo-nvidia",
    )
    assert out == ""


def test_ensure_empty_when_no_container_name():
    # no explicit name and none derivable from an empty url -> sidecar skipped, GPU off
    out = ensure_gpuinfo_sidecar("img:latest", "gpuinfo-net", "", container_name="")
    assert out == ""


def test_ensure_empty_when_network_absent(monkeypatch):
    # the compose-declared labelled network was not brought up -> the hub does NOT
    # recreate it (compose owns it); degrade to GPU-off
    container = _Container(networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    _install_fake_docker(monkeypatch, client=_FakeClient(run_container=container, network_present=False))
    out = ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        container_name="gpuinfo-nvidia",
    )
    assert out == ""


def test_ensure_empty_when_no_network_name():
    # no network resolved (the labelled compose network was not discovered and no env
    # override) -> sidecar skipped, GPU off, before docker is even contacted
    out = ensure_gpuinfo_sidecar("img:latest", "", "http://{hostname}:8000", container_name="gpuinfo-nvidia")
    assert out == ""


def test_ensure_stamps_container_role_label_and_passes_no_env(monkeypatch):
    # the hub stamps the container role label on the sidecar it creates; the sidecar's
    # own runtime spec (NVIDIA env, port, cmd) is baked in the image, so the hub passes
    # NO environment= to containers.run (no duplication)
    container = _Container(name="gpuinfo-nvidia", networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    client = _FakeClient(run_container=container)
    _install_fake_docker(monkeypatch, client=client)
    out = ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        compose_project="proj", container_name="gpuinfo-nvidia",
        container_role_label_key="hub.container.role",
        container_role_label_value="gpuinfo",
    )
    assert out == "http://172.20.0.7:8000"
    kw = client.containers.last_run_kwargs
    assert kw["labels"]["hub.container.role"] == "gpuinfo"
    assert "environment" not in kw


def test_ensure_requests_vendor_runtime_when_registered(monkeypatch):
    # gpu_runtime (the vendor provider's runtime, 'nvidia' today) is requested ONLY
    # when the docker host registers it.
    container = _Container(name="gpuinfo-nvidia", networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    client = _FakeClient(run_container=container, runtimes={"nvidia": {}})
    _install_fake_docker(monkeypatch, client=client)
    ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        container_name="gpuinfo-nvidia", gpu_runtime="nvidia",
    )
    assert client.containers.last_run_kwargs["runtime"] == "nvidia"


def test_ensure_omits_runtime_when_not_registered(monkeypatch):
    # vendor runtime asked for but the host does not register it -> not requested
    # (asking for an unregistered runtime would just fail the run).
    container = _Container(name="gpuinfo-nvidia", networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    client = _FakeClient(run_container=container)  # no runtimes registered
    _install_fake_docker(monkeypatch, client=client)
    ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        container_name="gpuinfo-nvidia", gpu_runtime="nvidia",
    )
    assert "runtime" not in client.containers.last_run_kwargs


def test_ensure_omits_runtime_when_no_vendor(monkeypatch):
    # no vendor runtime (gpu_runtime=None) -> never requested even if one is registered
    container = _Container(name="gpuinfo-nvidia", networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    client = _FakeClient(run_container=container, runtimes={"nvidia": {}})
    _install_fake_docker(monkeypatch, client=client)
    ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        container_name="gpuinfo-nvidia", gpu_runtime=None,
    )
    assert "runtime" not in client.containers.last_run_kwargs


def test_ensure_stamps_container_description_label(monkeypatch):
    # the hub stamps an informational hub.container.description label when a
    # description is supplied (mirrors the volume/network .description convention)
    container = _Container(name="gpuinfo-nvidia", networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    client = _FakeClient(run_container=container)
    _install_fake_docker(monkeypatch, client=client)
    ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        compose_project="proj", container_name="gpuinfo-nvidia",
        container_description_label_key="hub.container.description",
        container_description="GPU-info sidecar",
    )
    assert client.containers.last_run_kwargs["labels"]["hub.container.description"] == "GPU-info sidecar"


def test_ensure_omits_description_label_when_blank(monkeypatch):
    # no description supplied -> no description label (the default value is empty)
    container = _Container(name="gpuinfo-nvidia", networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    client = _FakeClient(run_container=container)
    _install_fake_docker(monkeypatch, client=client)
    ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        compose_project="proj", container_name="gpuinfo-nvidia",
    )
    assert "hub.container.description" not in client.containers.last_run_kwargs["labels"]


# ── compose-style naming: the hub replicates <project>-<service>-<number> ──────

def test_compose_container_name_matches_compose_convention():
    # exactly like compose auto-names a service container: <project>-<service>-<number>
    assert _compose_container_name("gpuinfo-nvidia", "proj") == "proj-gpuinfo-nvidia-1"


def test_compose_container_name_bare_without_project():
    # no project (hub not compose-managed) -> the bare service name, nothing to mirror
    assert _compose_container_name("gpuinfo-nvidia", "") == "gpuinfo-nvidia"


def test_ensure_runs_with_compose_qualified_name_and_simple_service_label(monkeypatch):
    # the created container's NAME is the compose-style FQN (<project>-<service>-1), while
    # com.docker.compose.service carries the SIMPLE service name and container-number the
    # ordinal - so it is indistinguishable from a compose-managed container
    container = _Container(name="proj-gpuinfo-nvidia-1", networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    client = _FakeClient(run_container=container)
    _install_fake_docker(monkeypatch, client=client)
    ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        compose_project="proj", container_name="gpuinfo-nvidia",
    )
    kw = client.containers.last_run_kwargs
    assert kw["name"] == "proj-gpuinfo-nvidia-1"
    assert kw["labels"]["com.docker.compose.service"] == "gpuinfo-nvidia"
    assert kw["labels"]["com.docker.compose.container-number"] == "1"
    assert kw["labels"]["com.docker.compose.project"] == "proj"


def test_ensure_bare_name_without_project(monkeypatch):
    # no project -> bare service name, no compose.* identity labels stamped
    container = _Container(name="gpuinfo-nvidia", networks={"gpuinfo-net": {"IPAddress": "172.20.0.7"}})
    client = _FakeClient(run_container=container)
    _install_fake_docker(monkeypatch, client=client)
    ensure_gpuinfo_sidecar(
        "img:latest", "gpuinfo-net", "http://{hostname}:8000",
        container_name="gpuinfo-nvidia",
    )
    kw = client.containers.last_run_kwargs
    assert kw["name"] == "gpuinfo-nvidia"
    assert "com.docker.compose.service" not in kw["labels"]


class _StopContainer:
    def __init__(self):
        self.removed = False

    def remove(self, force=False):
        self.removed = True


class _StopContainers:
    def __init__(self):
        self.got = None
        self.container = _StopContainer()

    def get(self, name):
        self.got = name
        return self.container


class _StopClient:
    def __init__(self):
        self.containers = _StopContainers()

    def close(self):
        pass


def test_stop_removes_the_compose_qualified_name(monkeypatch):
    # teardown must compute the SAME compose-style name the create path used, so it finds
    # and removes the exact container (not the bare service name)
    client = _StopClient()
    _install_fake_docker(monkeypatch, client=client)
    stop_gpuinfo_sidecar("http://{hostname}:8000", container_name="gpuinfo-nvidia", compose_project="proj")
    assert client.containers.got == "proj-gpuinfo-nvidia-1"
    assert client.containers.container.removed is True
