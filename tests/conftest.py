import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def site():
    """Render the site once per test session and return the _site directory."""
    result = subprocess.run(
        ["quarto", "render"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"quarto render failed:\n{result.stdout}\n{result.stderr}")
    out = REPO_ROOT / "_site"
    assert out.is_dir(), "quarto render did not produce _site/"
    return out


def read_html(site, relpath):
    """Read a generated HTML file as text."""
    path = site / relpath
    assert path.is_file(), f"expected generated file {relpath} to exist"
    return path.read_text(encoding="utf-8")
