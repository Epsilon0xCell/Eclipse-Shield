import os
import sys

import pytest

# Make the application modules importable no matter where pytest runs from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

API_KEY_ENV_VARS = ("GOOGLE_API_KEY", "GEMINI_API_KEY", "API_KEY",
                    "ECLIPSE_GEMINI_API_KEY")


@pytest.fixture()
def local_mode_env(monkeypatch, tmp_path):
    """Force local rules-only mode: no real Gemini key can leak into tests."""
    for var in API_KEY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ECLIPSE_API_KEY_FILE", str(tmp_path / "no-such-key.txt"))
    return tmp_path


@pytest.fixture()
def client(local_mode_env):
    from secure_app import create_app
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client
