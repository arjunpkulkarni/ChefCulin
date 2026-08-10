"""Palate Memory G1+G2: save writes, discard writes nothing, per-user scope."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from culin_etl.api import create_app
from culin_etl.palate import PalateStore, get_database_url

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://culin:culin@127.0.0.1:5432/culin"
)


def _db_up() -> bool:
    try:
        store = PalateStore(DATABASE_URL)
        store.ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="Postgres not available")


@pytest.fixture
def store():
    s = PalateStore(DATABASE_URL)
    s.ensure_schema()
    # isolate each test user
    yield s


@pytest.fixture
def user_id():
    return f"test-{uuid.uuid4()}"


@pytest.fixture
def sample_payload():
    return {
        "dish": [
            {"name": "duck", "lens": "compound", "mode": "sear"},
            {"name": "orange", "lens": "tradition", "mode": None},
        ],
        "form": {"name": "Seared magret", "desc": "crisp skin"},
        "cuisine_scope": {"label": "France", "keys": ["france"]},
        "source": "f6",
    }


def test_save_writes_record(store, user_id, sample_payload):
    before = store.list_for_user(user_id)
    assert before == []

    row = store.save(user_id=user_id, **sample_payload)
    assert row["id"]
    assert row["user_id"] == user_id
    assert row["dish"][0]["name"] == "duck"
    assert row["form"]["name"] == "Seared magret"
    assert row["cuisine_scope"]["keys"] == ["france"]
    assert row["source"] == "f6"

    after = store.list_for_user(user_id)
    assert len(after) == 1
    assert after[0]["id"] == row["id"]


def test_discard_writes_nothing(store, user_id, sample_payload):
    """F6 Discard = do not call save. Storage stays empty."""
    assert store.list_for_user(user_id) == []
    # explicit no-op helper documents the product rule
    store.discard()
    assert store.list_for_user(user_id) == []


def test_records_are_scoped_per_user(store, sample_payload):
    a = f"user-a-{uuid.uuid4()}"
    b = f"user-b-{uuid.uuid4()}"
    store.save(user_id=a, **sample_payload)
    store.save(user_id=b, **{**sample_payload, "form": {"name": "Confit"}})

    only_a = store.list_for_user(a)
    only_b = store.list_for_user(b)
    assert len(only_a) == 1
    assert len(only_b) == 1
    assert only_a[0]["form"]["name"] == "Seared magret"
    assert only_b[0]["form"]["name"] == "Confit"
    assert only_a[0]["id"] != only_b[0]["id"]


def test_roundtrip_get(store, user_id, sample_payload):
    saved = store.save(user_id=user_id, **sample_payload)
    loaded = store.get(saved["id"])
    assert loaded is not None
    assert loaded["id"] == saved["id"]
    assert loaded["dish"] == sample_payload["dish"]


def test_delete_saved_memory(store, user_id, sample_payload):
    saved = store.save(user_id=user_id, **sample_payload)
    assert store.delete(saved["id"], user_id=user_id) is True
    assert store.get(saved["id"]) is None
    assert store.list_for_user(user_id) == []


def test_api_save_and_list(store, user_id, sample_payload):
    app = create_app(
        artifacts={"cooccur": [], "ingredient_technique": [], "meta": {}},
        palate_store=store,
    )
    client = TestClient(app)

    res = client.post(
        "/palate",
        json={"user_id": user_id, **sample_payload},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["user_id"] == user_id

    listed = client.get("/palate", params={"user_id": user_id})
    assert listed.status_code == 200
    assert len(listed.json()["results"]) == 1

    # discard path: client simply does not POST — nothing new appears
    listed2 = client.get("/palate", params={"user_id": user_id})
    assert len(listed2.json()["results"]) == 1


def test_get_database_url_default():
    url = get_database_url()
    assert "postgresql" in url
