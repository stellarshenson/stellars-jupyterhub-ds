"""Guard tests for the html_templates_enhanced elimination (#419).

The custom Bootstrap template layer is deleted in full - the portal SPA owns every
user/admin journey and the few pages JupyterHub renders as framework plumbing fall back
to stock JupyterHub/NativeAuth. These tests fail if any build input reintroduces a
reference to the removed dir/assets, if the directory reappears, or if the Dockerfile
re-adds the COPY/cp lines. They also confirm the portal wheel still ships every template
name the portal itself renders.
"""
from pathlib import Path

import pytest

# tests/ -> duoptimum-hub-services/ -> jupyterhub/ -> services/ -> <repo root>.
# The image build copies ONLY this package into /src/duoptimum-hub-services and runs
# its tests there (Dockerfile STAGE 1), so the repo above does not exist in that
# context - these repo-integrity guards self-skip there and run for real from a full
# checkout (local / CI).
_here = Path(__file__).resolve()
REPO_ROOT = _here.parents[4] if len(_here.parents) > 4 else _here.parent
ENHANCED_DIR = REPO_ROOT / "services" / "jupyterhub" / "html_templates_enhanced"
DOCKERFILE = REPO_ROOT / "services" / "jupyterhub" / "Dockerfile.jupyterhub"
WHEEL_TEMPLATES = (
    REPO_ROOT / "services" / "jupyterhub" / "duoptimum-hub-web"
    / "duoptimum_hub_web" / "templates"
)

RELIC_TOKENS = ("html_templates_enhanced", "custom.css", "session-timer.js", "mobile.js")
# image build inputs only - test code that asserts ON these tokens lives under tests/
SCAN_EXTS = {".py", ".html", ".yml", ".yaml", ".sh", ".ts", ".tsx"}
SCAN_ROOTS = ("services", "config")
SKIP_DIRS = {
    "node_modules", "dist", "build", ".git", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".vite",
}

# repo-integrity guards apply only with a full checkout present (see header)
pytestmark = pytest.mark.skipif(
    not (REPO_ROOT / "services" / "jupyterhub").is_dir(),
    reason="requires a full repo checkout; skipped in the isolated package build",
)


def _iter_build_inputs():
    """Yield build-input files under the scan roots (plus Dockerfile*), skipping vendor
    dirs and this test file (which names the relic tokens on purpose)."""
    self_path = Path(__file__).resolve()
    for root_name in SCAN_ROOTS:
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.resolve() == self_path:
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix in SCAN_EXTS or p.name.startswith("Dockerfile"):
                yield p


def test_html_templates_enhanced_dir_gone():
    assert not ENHANCED_DIR.exists(), f"{ENHANCED_DIR} must be deleted"


def test_no_relic_references_in_build_inputs():
    offenders = []
    for p in _iter_build_inputs():
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for tok in RELIC_TOKENS:
            if tok in text:
                offenders.append(f"{p.relative_to(REPO_ROOT)}: {tok}")
    assert not offenders, "relic references remain:\n" + "\n".join(offenders)


def test_dockerfile_no_relic_copies():
    text = DOCKERFILE.read_text(encoding="utf-8")
    for tok in RELIC_TOKENS:
        assert tok not in text, f"Dockerfile still references {tok}"
    # the stock admin-react.js removal must still be present
    assert "admin-react.js" in text


def test_wheel_provides_required_template_names():
    required = {
        "home.html", "admin.html", "token.html", "portal.html",
        "duoptimum_login.html", "duoptimum_signup.html",
    }
    present = {p.name for p in WHEEL_TEMPLATES.glob("*.html")}
    missing = required - present
    assert not missing, f"wheel template_dir missing: {missing}"
