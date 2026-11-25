"""Regression tests for the 2026-11-24 audit fixes.

Each test names the bug it guards. All run keyless and offline; the
Gemini client is a clearly labeled fixture with the google-genai
call shape.
"""

import pytest

from script import ProductivityAnalyzer, host_matches_entry
from security import InputValidator


# ------------------------------------------------------- host boundaries

@pytest.mark.parametrize("host,entry,expected", [
    ("youtube.com", "youtube.com", True),
    ("www.youtube.com", "youtube.com", True),
    ("notyoutube.com", "youtube.com", False),
    ("youtube.com.evil.com", "youtube.com", False),
    ("notion.so", "notion", True),
    ("canvas.instructure.com", "canvas", True),
    ("evilnotion.com", "notion", False),
    ("notion.so.evil.com", "notion.so", False),
])
def test_host_matches_entry(host, entry, expected):
    assert host_matches_entry(host, entry) is expected


def test_allowed_platform_needs_host_match_not_url_text(local_mode_env):
    analyzer = ProductivityAnalyzer()
    # Platform name in the path or query is not the platform.
    assert analyzer._is_allowed_platform("https://example.com/notion", "work") is False
    assert analyzer._is_allowed_platform("https://example.com/?next=notion", "work") is False
    assert analyzer._is_allowed_platform("https://evilnotion.com/page", "work") is False
    assert analyzer._is_allowed_platform("https://notion.so/page", "work") is True


def test_blocked_specific_needs_host_boundary(client):
    # notyoutube.com must not trip the youtube.com rule. It is decided
    # by local category rules instead, which is a different explanation.
    resp = client.post("/analyze", json={
        "url": "https://notyoutube.com/page", "domain": "work"})
    assert resp.status_code == 200
    assert "Blocked specific" not in resp.get_json()["explanation"]


# ------------------------------------------------------------ URL validity

@pytest.mark.parametrize("url", [
    "https://example.technology/page",
    "https://example.international/",
    "https://sub.example.museum/x",
])
def test_validate_url_accepts_long_tlds(url):
    assert InputValidator.validate_url(url) is True


@pytest.mark.parametrize("url", [
    "https://user:pass@example.com/page",
    "https://example.com@evil.com/",
    "http://2130706433/admin",      # integer form of 127.0.0.1
    "http://0x7f000001/admin",      # hex form of 127.0.0.1
    "http://169.254.169.254/latest/meta-data/",
])
def test_validate_url_rejects_credentials_and_obfuscated_loopback(url):
    assert InputValidator.validate_url(url) is False


def test_analyze_accepts_long_tld_site(client):
    resp = client.post("/analyze", json={
        "url": "https://example.technology/page", "domain": "work"})
    assert resp.status_code == 200


# ------------------------------------------------------------ /api/check

def test_api_check_contract_keyless(client):
    resp = client.post("/api/check", json={
        "url": "https://youtube.com/watch?v=abc", "profile": "work"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["allowed"] is False
    assert data["source"] == "list"
    assert data["profile"] == "work"
    assert data["reason"]


def test_api_check_accepts_domain_alias_and_reports_keyless_source(client):
    resp = client.post("/api/check", json={
        "url": "https://example.com/page", "domain": "work"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["allowed"] is False
    assert data["source"] == "keyless-default"


def test_api_check_malformed_is_400(client):
    assert client.post("/api/check", json={
        "url": "file:///etc/passwd", "profile": "work"}).status_code == 400
    assert client.post("/api/check", json={
        "url": "https://example.com", "profile": "nope"}).status_code == 400
    assert client.post("/api/check", json={}).status_code == 400


# ------------------------------------------------------------- rate limits

def test_health_is_not_rate_limited(client):
    codes = [client.get("/health").status_code for _ in range(105)]
    assert codes == [200] * 105


def test_no_unsafe_eval_in_csp(client):
    for path in ("/", "/extension/popup.html"):
        csp = client.get(path).headers.get("Content-Security-Policy", "")
        assert "unsafe-eval" not in csp


# ------------------------------------------------- Gemini seam (fixture)

class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self, text):
        self._text = text
        self.calls = 0

    def generate_content(self, model=None, contents=None, config=None):
        self.calls += 1
        return _FakeResponse(self._text)


class _FakeClient:
    """Fixture with the google-genai client shape. Not a real client."""

    def __init__(self, text):
        self.models = _FakeModels(text)


def _analyzer_with_fake_client(local_mode_env):
    analyzer = ProductivityAnalyzer(api_key="fixture-key-not-real")
    analyzer._client = _FakeClient(
        '{"allowed": true, "category": "other", '
        '"reason": "Fixture structured verdict", "confidence": 0.9}')
    analyzer.model = analyzer._client
    analyzer.ai_available = True
    return analyzer


def test_structured_gemini_verdict_and_cache(local_mode_env):
    analyzer = _analyzer_with_fake_client(local_mode_env)
    first = analyzer.analyze_website("https://unknown-site-123.com/a", "work")
    assert first["isProductive"] is True
    assert first["explanation"] == "Fixture structured verdict"
    assert first["source"] == "gemini"
    second = analyzer.analyze_website("https://unknown-site-123.com/b", "work")
    assert second["source"] == "cache"
    # Second verdict for the same host came from the cache, not the API.
    assert analyzer._client.models.calls == 1


def test_extension_pages_use_no_remote_fonts():
    # Regression (found in the 2026-11-24 exhaustive test pass):
    # block.html imported Share Tech Mono from Google Fonts and
    # newtab.html listed a fonts.gstatic.com fallback, while popup.html
    # already used the bundled local face. Extension pages must load
    # fonts from the package: remote imports fail offline and leak the
    # page view to a third party.
    import pathlib
    ext = pathlib.Path(__file__).resolve().parent.parent / "extension"
    for name in ("block.html", "newtab.html", "popup.html", "sidepanel.html"):
        text = (ext / name).read_text()
        assert "fonts.googleapis.com" not in text, name
        assert "fonts.gstatic.com" not in text, name


def test_gemini_failure_degrades_to_ai_unavailable(local_mode_env):
    analyzer = _analyzer_with_fake_client(local_mode_env)

    def boom(model=None, contents=None, config=None):
        raise RuntimeError("fixture backend failure")

    analyzer._client.models.generate_content = boom
    result = analyzer.analyze_website("https://github.com/some/repo", "work")
    assert result["isProductive"] is True
    assert result["source"] == "ai-unavailable"
    assert "fixture backend failure" not in result["explanation"]


def test_extension_pages_use_sni_theme():
    """SNI retheme: extension pages carry BF00FF on black, no Matrix green."""
    from pathlib import Path
    ext = Path(__file__).resolve().parent.parent / "extension"
    for name in ("popup.html", "sidepanel.html", "block.html", "newtab.html"):
        body = (ext / name).read_text(encoding="utf-8")
        assert "#BF00FF" in body, name
        assert "#0f0" not in body.lower().replace("#bf00ff", ""), name
