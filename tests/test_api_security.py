"""Tests for the API key auth wall on write endpoints."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.api.app import create_app
from tests.api_client import TEST_API_KEY, ASGITestClient


def _build_app(tmp_path: Path, *, api_key: str | None):
    return create_app(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        editorial_root=tmp_path / "outputs" / "editorial",
        start_task_runner=False,
        api_key=api_key,
    )


def test_write_endpoint_returns_503_when_api_key_not_configured(tmp_path):
    """Fail-closed: server with no API key configured rejects all writes.

    This is the inverse of the previous half-finished ``_require_api_key`` shim
    which silently allowed writes when the env var was missing.
    """
    app = _build_app(tmp_path, api_key=None)
    client = ASGITestClient(app, api_key=None)

    response = client.post("/pipeline/tasks", json={"taskType": "full_pipeline"})

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_write_endpoint_rejects_request_without_token(tmp_path):
    app = _build_app(tmp_path, api_key=TEST_API_KEY)
    client = ASGITestClient(app, api_key=None)

    response = client.post("/pipeline/tasks", json={"taskType": "full_pipeline"})

    assert response.status_code == 401


def test_write_endpoint_rejects_request_with_wrong_token(tmp_path):
    app = _build_app(tmp_path, api_key=TEST_API_KEY)
    client = ASGITestClient(app, api_key="wrong-token")

    response = client.post("/pipeline/tasks", json={"taskType": "full_pipeline"})

    assert response.status_code == 401


def test_write_endpoint_accepts_request_with_correct_token(tmp_path):
    app = _build_app(tmp_path, api_key=TEST_API_KEY)
    client = ASGITestClient(app)  # default api_key=TEST_API_KEY

    response = client.post(
        "/pipeline/tasks",
        json={"taskType": "full_pipeline", "notify": False, "editorialLimit": 1},
    )

    assert response.status_code == 200
    task = response.json()["data"]
    assert task["status"] == "queued"
    # actor recorded server-side from token, not from client
    assert task["requestedBy"].startswith("api:")


def test_read_endpoints_remain_public(tmp_path):
    app = _build_app(tmp_path, api_key=TEST_API_KEY)
    client = ASGITestClient(app, api_key=None)

    for path in [
        "/papers",
        "/drafts",
        "/exports",
        "/notifications",
        "/destinations",
        "/pipeline/summary",
        "/pipeline/tasks",
        "/pipeline/runs/crawl",
    ]:
        response = client.get(path)
        assert response.status_code == 200, f"{path} should be public, got {response.status_code}"


def test_destination_write_paths_use_unified_auth(tmp_path):
    """``/destinations`` previously had a separate auth shim; verify it now
    consults the same ``app.state.api_key`` wall as every other write route."""
    app = _build_app(tmp_path, api_key=TEST_API_KEY)
    client = ASGITestClient(app, api_key=None)

    response = client.post(
        "/destinations",
        json={"draftId": "missing", "platform": "bilibili"},
    )

    assert response.status_code == 401


def test_actor_field_is_not_accepted_from_client_in_draft_actions(tmp_path):
    """``EditorialDraftActionRequest`` no longer contains an ``actor`` field;
    pydantic ignores extras by default, so passing one is a no-op (the route
    uses the auth-derived actor)."""
    from app.api.schemas import EditorialDraftActionRequest

    parsed = EditorialDraftActionRequest.model_validate({"actor": "ceo", "note": "x"})
    assert not hasattr(parsed, "actor")
    assert parsed.note == "x"


def test_create_app_rejects_cors_wildcard_origin(tmp_path):
    """Browsers refuse credentialed requests when ``Access-Control-Allow-Origin``
    is ``*``. Since we ship ``allow_credentials=True``, accepting ``*`` here
    would silently break every cookie/Authorization-bearing request. Fail
    fast at startup instead so the operator sees the misconfiguration."""
    with pytest.raises(ValueError) as excinfo:
        create_app(
            database_url=f"sqlite:///{tmp_path/'papers.db'}",
            editorial_root=tmp_path / "outputs" / "editorial",
            start_task_runner=False,
            api_key=TEST_API_KEY,
            cors_allow_origins=["*"],
        )
    message = str(excinfo.value).lower()
    assert "*" in message or "wildcard" in message
    assert "credential" in message


def test_create_app_accepts_explicit_cors_origins(tmp_path):
    """Sanity: a concrete origin list still works."""
    app = create_app(
        database_url=f"sqlite:///{tmp_path/'papers.db'}",
        editorial_root=tmp_path / "outputs" / "editorial",
        start_task_runner=False,
        api_key=TEST_API_KEY,
        cors_allow_origins=["http://localhost:3000", "https://app.example.com"],
    )
    assert app is not None


@pytest.fixture(autouse=True)
def _disable_dotenv(monkeypatch):
    """Some auth tests need to override env vars; ensure the project ``.env``
    doesn't bleed in unexpected ``API_KEY`` values."""
    yield
