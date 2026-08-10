"""HTTP acceptance: top-N cooccur + techniques endpoints."""

from fastapi.testclient import TestClient

from culin_etl.api import create_app


def test_cooccur_endpoint(artifacts):
    app = create_app(artifacts)
    client = TestClient(app)
    res = client.get("/cooccur", params={"ingredient": "duck", "n": 10})
    assert res.status_code == 200
    data = res.json()
    assert data["ingredient"] == "duck"
    assert data["canonical"] == "duck"
    assert len(data["results"]) <= 10
    assert any(r["ingredient"] == "orange" for r in data["results"])
    assert all("freq" in r and "confidence" in r for r in data["results"])


def test_techniques_endpoint(artifacts):
    app = create_app(artifacts)
    client = TestClient(app)
    res = client.get("/techniques", params={"ingredient": "duck", "n": 10})
    assert res.status_code == 200
    data = res.json()
    assert data["ingredient"] == "duck"
    techs = [r["technique"] for r in data["results"]]
    assert "sear" in techs or "roast" in techs


def test_unknown_ingredient_returns_empty(artifacts):
    app = create_app(artifacts)
    client = TestClient(app)
    res = client.get("/cooccur", params={"ingredient": "unicorn dust", "n": 5})
    assert res.status_code == 200
    assert res.json()["results"] == []


def test_health_and_meta(artifacts):
    app = create_app(artifacts)
    client = TestClient(app)
    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["ok"] is True
    assert h.json()["cooccur_edges"] > 0
    m = client.get("/meta")
    assert m.status_code == 200
