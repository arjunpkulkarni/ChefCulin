from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from culin_etl.build import load_artifact_tables
from culin_etl.lookup import index_cooccur, index_techniques, top_cooccur, top_techniques
from culin_etl.normalize import canonicalize
from culin_etl.palate import PalateStore, get_database_url

DEFAULT_ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts" / "corpus"


class PalateSaveBody(BaseModel):
    user_id: str
    dish: list[Any] = Field(default_factory=list)
    form: Optional[dict] = None
    cuisine_scope: Optional[dict] = None
    source: str = "f6"


def create_app(
    artifacts: Optional[dict] = None,
    artifacts_dir: Optional[Path] = None,
    palate_store: Optional[PalateStore] = None,
) -> FastAPI:
    """
    Serve precomputed cooccur/technique tables + Palate Memory.

    Artifacts: offline RecipeNLG tables (Lens 3 / techniques).
    Palate: Postgres store for F6 Save (per-user). Discard = no write.
    """
    if artifacts is None:
        root = Path(artifacts_dir or os.environ.get("CULIN_ARTIFACTS", DEFAULT_ARTIFACTS))
        if (root / "cooccur.jsonl").exists():
            artifacts = load_artifact_tables(root)
            artifacts["_dir"] = str(root.resolve())
        else:
            artifacts = {
                "cooccur": [],
                "ingredient_technique": [],
                "meta": {},
                "_dir": str(root.resolve()),
            }
    else:
        artifacts.setdefault("_dir", "memory")

    co_idx = index_cooccur(artifacts["cooccur"])
    tech_idx = index_techniques(artifacts["ingredient_technique"])

    store = palate_store
    if store is None and os.environ.get("CULIN_DISABLE_PALATE") != "1":
        try:
            candidate = PalateStore(get_database_url())
            candidate.ping()
            candidate.ensure_schema()
            store = candidate
        except Exception:
            store = None

    app = FastAPI(
        title="CulinAI API",
        version="0.2.0",
        description="Artifact lookups + Palate Memory store",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        palate_ok = False
        if store is not None:
            try:
                palate_ok = store.ping()
            except Exception:
                palate_ok = False
        return {
            "ok": True,
            "artifacts": artifacts.get("_dir"),
            "cooccur_edges": len(artifacts["cooccur"]),
            "technique_edges": len(artifacts["ingredient_technique"]),
            "palate_db": palate_ok,
        }

    @app.get("/meta")
    def meta():
        return artifacts.get("meta") or {}

    @app.get("/cooccur")
    def cooccur(
        ingredient: str = Query(..., description="Ingredient name (canonicalized)"),
        n: int = Query(10, ge=1, le=100),
    ):
        key = canonicalize(ingredient) or ingredient.strip().lower()
        return {
            "ingredient": ingredient,
            "canonical": key,
            "results": top_cooccur(
                artifacts["cooccur"], ingredient, n=n, index=co_idx
            ),
        }

    @app.get("/techniques")
    def techniques(
        ingredient: str = Query(..., description="Ingredient name (canonicalized)"),
        n: int = Query(10, ge=1, le=100),
    ):
        key = canonicalize(ingredient) or ingredient.strip().lower()
        return {
            "ingredient": ingredient,
            "canonical": key,
            "results": top_techniques(
                artifacts["ingredient_technique"], ingredient, n=n, index=tech_idx
            ),
        }

    # ---------- Palate Memory ----------

    def _require_store() -> PalateStore:
        if store is None:
            raise HTTPException(
                status_code=503,
                detail="Palate DB unavailable. Start Postgres: docker compose up -d",
            )
        return store

    @app.post("/palate", status_code=201)
    def palate_save(body: PalateSaveBody):
        """F6 Save → persist snapshot. F6 Discard → do not call this."""
        s = _require_store()
        try:
            row = s.save(
                user_id=body.user_id,
                dish=body.dish,
                form=body.form,
                cuisine_scope=body.cuisine_scope,
                source=body.source,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return row

    @app.get("/palate")
    def palate_list(
        user_id: str = Query(...),
        limit: int = Query(50, ge=1, le=200),
    ):
        s = _require_store()
        return {"user_id": user_id, "results": s.list_for_user(user_id, limit=limit)}

    @app.get("/palate/{memory_id}")
    def palate_get(memory_id: str):
        s = _require_store()
        row = s.get(memory_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Not found")
        return row

    @app.delete("/palate/{memory_id}")
    def palate_delete(memory_id: str, user_id: str = Query(...)):
        s = _require_store()
        ok = s.delete(memory_id, user_id=user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Not found")
        return {"deleted": True, "id": memory_id}

    return app


def app_factory() -> FastAPI:
    """uvicorn entry: uvicorn culin_etl.api:app_factory --factory"""
    return create_app()
