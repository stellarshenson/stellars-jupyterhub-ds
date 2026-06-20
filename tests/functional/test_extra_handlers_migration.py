"""Migration off the deprecated c.JupyterHub.extra_handlers (DuoptimumHub subclass).

End-to-end proof on the rebuilt image that:
- the hub launches via the duoptimum-hub entry point with NO extra_handlers
  deprecation warning and NO unrecognized-config warning for registered_handlers
- every route the old extra_handlers owned still resolves identically: custom
  /api/* live, /health up, unknown /hub/api/* -> JSON 404 (API404 still wins),
  /hub/logo serves an image (portal catch-all does not shadow it), portal shell
  served at /hub/home, stock /hub/login intact.
"""

import pytest

HUB_CONTAINER = "stellars-functest-duoptimum-hub"


def _hub_logs(docker_client):
    return docker_client.containers.get(HUB_CONTAINER).logs().decode("utf-8", "replace")


@pytest.mark.acc_crit(
    "extra-handlers-migration::No deprecation warning",
    "extra-handlers-migration::Trait-section hygiene",
)
def test_no_extra_handlers_deprecation_or_config_warning(docker_client):
    logs = _hub_logs(docker_client)
    assert "extra_handlers is deprecated" not in logs, \
        "deprecated extra_handlers trait was triggered"
    # traitlets prints "Config option `x` not recognized by `JupyterHub`." when a
    # section/trait does not bind - registered_handlers must bind to DuoptimumHub.
    assert "registered_handlers` not recognized" not in logs, \
        "registered_handlers did not bind to the launched app class"


@pytest.mark.acc_crit("extra-handlers-migration::Custom API live")
def test_custom_api_live(admin_api, base_url):
    r = admin_api.get(f"{base_url}/hub/api/settings", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/json")


@pytest.mark.acc_crit("extra-handlers-migration::Health endpoint")
def test_health_endpoint(admin_api, base_url):
    r = admin_api.get(f"{base_url}/hub/health", timeout=30)
    assert r.status_code == 200


@pytest.mark.acc_crit("extra-handlers-migration::Edge: unknown /hub/api/*")
def test_unknown_api_is_json_404_not_shell(admin_api, base_url):
    r = admin_api.get(f"{base_url}/hub/api/does-not-exist-xyz", timeout=30)
    assert r.status_code == 404
    # API404 returns JSON; the SPA catch-all would have returned text/html
    assert r.headers.get("content-type", "").startswith("application/json"), \
        "unknown /hub/api/* fell through to the SPA shell instead of API404"


@pytest.mark.acc_crit("extra-handlers-migration::Edge: /hub/logo")
def test_logo_serves_image_not_shell(admin_api, base_url):
    r = admin_api.get(f"{base_url}/hub/logo", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/"), \
        "/hub/logo served the SPA shell instead of the logo image"


@pytest.mark.acc_crit("extra-handlers-migration::Portal landing")
def test_portal_home_serves_shell(admin_api, base_url):
    r = admin_api.get(f"{base_url}/hub/home", timeout=30)
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    # the portal shell injects the hub data (xsrf token) - a bare built-in would not
    assert "jhdata" in r.text


@pytest.mark.acc_crit("extra-handlers-migration::Built-ins intact")
def test_login_built_in_intact(admin_api, base_url):
    r = admin_api.get(f"{base_url}/hub/login", timeout=30)
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
