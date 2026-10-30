"""End-to-end tests for Eclipse Shield.

These tests run the real Flask app and the real analyzer in local
rules-only mode (no Gemini API key), plus the AI code paths against a
clearly labeled fixture model. No test here stubs the security checks
themselves: validation, rate limiting, and the allow/block rules under
test are the production implementations.
"""

import pytest

from script import ProductivityAnalyzer


# I exercise the AI paths with the fixture model below, never with a
# real key. The fixture returns one canned line, so a test failure here
# is about my parsing and decision code, not about a network call or a
# provider changing its answers between runs.
class FixtureResponse:
    def __init__(self, text):
        self.text = text


class FixtureModel:
    """Test fixture only. Not a real AI model.

    Returns a canned decision string so the AI parsing path in
    ProductivityAnalyzer can be exercised without network access or a
    real API key.
    """

    def __init__(self, text="ALLOW: Fixture model decision"):
        self._text = text

    def generate_content(self, prompt, request_options=None):
        return FixtureResponse(self._text)


class FailingFixtureModel:
    """Test fixture only. Simulates an AI backend that errors out."""

    def generate_content(self, prompt, request_options=None):
        raise RuntimeError("fixture backend failure")


# ---------------------------------------------------------------- smoke

def test_health_reports_local_mode(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    # No key is configured in tests, and health must say so honestly.
    assert data["ai"] == "local-only"


def test_root_serves_popup(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"<html" in resp.data.lower()


def test_app_starts_from_any_working_directory(local_mode_env, monkeypatch, tmp_path):
    # Regression test: config used to load via CWD-relative paths, so
    # launching from another directory crashed startup.
    from secure_app import create_app
    monkeypatch.chdir(tmp_path)
    app = create_app()
    with app.test_client() as test_client:
        resp = test_client.get("/health")
        assert resp.status_code == 200
        assert test_client.get("/extension/popup.html").status_code == 200


# ------------------------------------------------------- security headers

def test_security_headers(client):
    resp = client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in resp.headers
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    # HSTS is correctly absent over plain HTTP on localhost.
    assert "Strict-Transport-Security" not in resp.headers


def test_csrf_token_header(client):
    resp = client.get("/")
    assert resp.headers.get("X-CSRF-Token")


# -------------------------------------------------------- extension files

def test_extension_files_served_including_nested(client):
    assert client.get("/extension/popup.html").status_code == 200
    # Nested assets used to break twice over: the built-in static route
    # shadowed the checked view, and secure_filename stripped slashes.
    resp = client.get("/extension/matrix-animation/js/main.js")
    assert resp.status_code == 200
    assert b"makeConfig" in resp.data


def test_extension_disallowed_file_type_blocked(client):
    # .c sources are not web assets and are not on the allowlist.
    resp = client.get("/extension/matrix-animation/playdate/matrix_c/main.c")
    assert resp.status_code == 403


def test_extension_traversal_blocked(client):
    assert client.get("/extension/../settings.json").status_code == 404
    assert client.get("/extension/.env").status_code == 404
    resp = client.get("/extension/%2e%2e%2f%2e%2e%2fetc%2fpasswd")
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------- analyze

def test_analyze_blocked_specific(client):
    resp = client.post("/analyze", json={
        "url": "https://youtube.com/watch?v=abc", "domain": "work"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["isProductive"] is False
    assert "Blocked specific" in data["explanation"]


def test_analyze_allowed_platform(client):
    resp = client.post("/analyze", json={
        "url": "https://notion.so/some-page", "domain": "work"})
    assert resp.status_code == 200
    assert resp.get_json()["isProductive"] is True


def test_analyze_local_fallback_allows_dev_site_without_key(client):
    # github.com is in no profile's allowlist, so without a key this is
    # decided by the local category rules, and must not hang or 500.
    resp = client.post("/analyze", json={
        "url": "https://github.com/some/repo", "domain": "work"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["isProductive"] is True
    assert "local rules" in data["explanation"]


def test_analyze_local_fallback_blocks_unknown_site(client):
    resp = client.post("/analyze", json={
        "url": "https://example.com/page", "domain": "work"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["isProductive"] is False
    assert "local rules" in data["explanation"]


def test_analyze_unknown_profile_is_400(client):
    resp = client.post("/analyze", json={
        "url": "https://example.com/page", "domain": "example.com"})
    assert resp.status_code == 400


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "file:///etc/passwd",
    "ftp://example.com/file",
    "http://192.168.1.1/admin",
    "http://10.0.0.5/admin",
    "http://localhost:8080/admin",
    "http://127.0.0.1:22/",
])
def test_analyze_rejects_dangerous_urls(client, url):
    resp = client.post("/analyze", json={"url": url, "domain": "work"})
    assert resp.status_code == 400


def test_analyze_rejects_traversal_domain(client):
    resp = client.post("/analyze", json={
        "url": "https://example.com", "domain": "../../../etc/passwd"})
    assert resp.status_code == 400


def test_analyze_missing_fields_is_400(client):
    assert client.post("/analyze", json={}).status_code == 400
    assert client.post("/analyze", json={"url": "https://example.com"}).status_code == 400


def test_analyze_invalid_json_is_400(client):
    resp = client.post("/analyze", data="not json",
                       content_type="application/json")
    assert resp.status_code == 400


# ------------------------------------------------------------- get_question

def test_get_question_local_flow_terminates(client):
    first = client.post("/get_question", json={"domain": "work", "context": []})
    assert first.status_code == 200
    q1 = first.get_json()["question"]
    assert q1 == ProductivityAnalyzer.FALLBACK_QUESTIONS[0]

    second = client.post("/get_question", json={
        "domain": "work",
        "context": [{"question": q1, "answer": "Building a web app"}]})
    q2 = second.get_json()["question"]
    assert q2 == ProductivityAnalyzer.FALLBACK_QUESTIONS[1]

    done = client.post("/get_question", json={
        "domain": "work",
        "context": [{"question": q1, "answer": "Building a web app"},
                    {"question": q2, "answer": "Ship the feature"}]})
    assert done.get_json()["question"] == "DONE"


def test_get_question_accepts_mapping_context(client):
    resp = client.post("/get_question", json={
        "domain": "work",
        "context": {"What specific task are you working on?": "Writing code"}})
    assert resp.status_code == 200
    assert resp.get_json()["question"] == ProductivityAnalyzer.FALLBACK_QUESTIONS[1]


def test_get_question_unknown_profile_is_400(client):
    resp = client.post("/get_question", json={"domain": "example.com", "context": []})
    assert resp.status_code == 400


# ------------------------------------------------------------ rate limiting

def test_failed_attempts_do_not_lock_out_whole_app(client):
    # Regression test: the failed-attempt throttle used to be enforced on
    # every route, so ten invalid /analyze inputs locked /health and the
    # extension files for the same IP for an hour.
    bad = {"url": "javascript:alert(1)", "domain": "work"}
    for _ in range(12):
        client.post("/analyze", json=bad)
    assert client.get("/health").status_code == 200
    assert client.get("/extension/popup.html").status_code == 200
    assert client.get("/").status_code == 200


def test_rate_limiting(client):
    payload = {"url": "https://youtube.com/watch?v=abc", "domain": "work"}
    codes = [client.post("/analyze", json=payload).status_code for _ in range(15)]
    assert 429 in codes


# ------------------------------------------------------------------- xss

def test_block_page_does_not_reflect_raw_payload(client):
    payload = "<script>alert(1)</script>"
    resp = client.get("/block", query_string={"reason": payload})
    assert resp.status_code == 200
    assert payload.encode() not in resp.data


# ------------------------------------------------------- analyzer unit level

def test_analyzer_starts_without_api_key(local_mode_env):
    analyzer = ProductivityAnalyzer(api_key="")
    assert analyzer.ai_available is False
    assert analyzer.model is None


def test_analyzer_ai_path_with_fixture_model(local_mode_env):
    analyzer = ProductivityAnalyzer(api_key="fixture-key-not-real",
                                    model=FixtureModel())
    assert analyzer.ai_available is True
    result = analyzer.analyze_website("https://unknown-site-123.com/page", "work")
    assert result["isProductive"] is True
    assert result["explanation"] == "Fixture model decision"


def test_analyzer_ai_failure_falls_back_to_local_rules(local_mode_env):
    analyzer = ProductivityAnalyzer(api_key="fixture-key-not-real",
                                    model=FailingFixtureModel())
    result = analyzer.analyze_website("https://github.com/some/repo", "work")
    assert result["isProductive"] is True
    assert "local rules" in result["explanation"]
    # Internal exception text must not leak to clients.
    assert "fixture backend failure" not in result["explanation"]


def test_analyzer_get_next_question_with_fixture_model(local_mode_env):
    analyzer = ProductivityAnalyzer(
        api_key="fixture-key-not-real",
        model=FixtureModel("What are you building today?"))
    result = analyzer.get_next_question("work", [])
    assert result["question"] == "What are you building today?"
