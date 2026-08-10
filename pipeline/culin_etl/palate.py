from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import psycopg
from psycopg.rows import dict_row

DEFAULT_DATABASE_URL = "postgresql://culin:culin@127.0.0.1:5432/culin"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "sql" / "001_palate.sql"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


class PalateStore:
    """
    Palate Memory store (MVP).

    Persist F6 Save snapshots per user. Discard is a no-write — call discard()
    only to document intent; it does not touch the DB.
    """

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or get_database_url()

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def ping(self) -> bool:
        with self._connect() as conn:
            conn.execute("SELECT 1")
        return True

    def ensure_schema(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.execute(sql)
            conn.commit()

    def discard(self) -> None:
        """F6 Discard: deliberately do nothing. No row is written."""
        return None

    def save(
        self,
        *,
        user_id: str,
        dish: list[Any],
        form: Optional[dict] = None,
        cuisine_scope: Optional[dict] = None,
        source: str = "f6",
    ) -> dict:
        if not user_id or not str(user_id).strip():
            raise ValueError("user_id is required")
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO palate_memories (user_id, dish, form, cuisine_scope, source)
                VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                RETURNING id, user_id, dish, form, cuisine_scope, source, created_at
                """,
                (
                    str(user_id).strip(),
                    json.dumps(dish),
                    json.dumps(form) if form is not None else None,
                    json.dumps(cuisine_scope) if cuisine_scope is not None else None,
                    source or "f6",
                ),
            ).fetchone()
            conn.commit()
        return _serialize(row)

    def get(self, memory_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, user_id, dish, form, cuisine_scope, source, created_at
                FROM palate_memories
                WHERE id = %s::uuid
                """,
                (memory_id,),
            ).fetchone()
        return _serialize(row) if row else None

    def list_for_user(self, user_id: str, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, dish, form, cuisine_scope, source, created_at
                FROM palate_memories
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            ).fetchall()
        return [_serialize(r) for r in rows]

    def delete(self, memory_id: str, *, user_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                DELETE FROM palate_memories
                WHERE id = %s::uuid AND user_id = %s
                RETURNING id
                """,
                (memory_id, user_id),
            )
            gone = cur.fetchone() is not None
            conn.commit()
        return gone


def _serialize(row: dict) -> dict:
    out = dict(row)
    if out.get("id") is not None:
        out["id"] = str(out["id"])
    if out.get("created_at") is not None:
        out["created_at"] = out["created_at"].isoformat()
    return out
