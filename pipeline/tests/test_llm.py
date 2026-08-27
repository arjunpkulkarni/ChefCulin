"""LLM proxy endpoint — mocked OpenAI, no network."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from culin_etl.api import create_app


def test_llm_chat_requires_key(artifacts, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(artifacts)
    client = TestClient(app)
    res = client.post("/llm/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert res.status_code == 503


def test_llm_chat_proxies(artifacts, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    app = create_app(artifacts)
    client = TestClient(app)

    fake = {
        "id": "chatcmpl-test",
        "choices": [{"message": {"role": "assistant", "content": '{"options":[]}'}}],
    }

    with patch("culin_etl.llm.httpx.AsyncClient") as Client:
        instance = Client.return_value.__aenter__.return_value
        instance.post = AsyncMock(
            return_value=type(
                "R",
                (),
                {"status_code": 200, "json": lambda self=None: fake, "text": ""},
            )()
        )
        res = client.post(
            "/llm/chat",
            json={
                "messages": [{"role": "user", "content": "Sichuan chicken"}],
                "temperature": 0.2,
            },
        )

    assert res.status_code == 200
    assert res.json()["choices"][0]["message"]["content"] == '{"options":[]}'


def test_health_reports_openai_flag(artifacts, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = create_app(artifacts)
    client = TestClient(app)
    h = client.get("/health").json()
    assert h["openai"] is False
