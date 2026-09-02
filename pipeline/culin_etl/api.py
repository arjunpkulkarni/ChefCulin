from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from culin_etl.build import load_artifact_tables
from culin_etl.compound_network import index_neighbors, top_compound_neighbors
from culin_etl.lookup import index_cooccur, index_techniques, top_cooccur, top_techniques
from culin_etl.normalize import canonicalize
from culin_etl.palate import PalateStore, get_database_url
from culin_etl.vcf_serve import DEFAULT_VCF, empty_vcf_tables, load_vcf_tables

DEFAULT_ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts" / "corpus"
DEFAULT_COMPOUND = Path(__file__).resolve().parents[1] / "artifacts" / "compound"

# Which table the Compound lens answers from. "pairs" is the VCF compound layer;
# "flavor_network" is the vendored Ahn/FooDB projection the prototype shipped on.
COMPOUND_SOURCE = os.environ.get("CULIN_COMPOUND_SOURCE", "pairs")


class LlmChatBody(BaseModel):
    """An OpenAI chat-completions body, minus the credential."""

    messages: list[dict] = Field(default_factory=list)
    model: Optional[str] = None
    temperature: Optional[float] = None
    tools: Optional[list[dict]] = None
    tool_choice: Optional[Any] = None
    response_format: Optional[dict] = None
    max_tokens: Optional[int] = None


class PalateSaveBody(BaseModel):
    user_id: str
    dish: list[Any] = Field(default_factory=list)
    form: Optional[dict] = None
    cuisine_scope: Optional[dict] = None
    source: str = "f6"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_compound_tables(compound_dir: Path) -> dict:
    root = Path(compound_dir)
    meta_path = root / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    neighbors = _load_jsonl(root / "neighbors.jsonl")
    return {"neighbors": neighbors, "meta": meta, "_dir": str(root.resolve())}


def create_app(
    artifacts: Optional[dict] = None,
    artifacts_dir: Optional[Path] = None,
    compound: Optional[dict] = None,
    compound_dir: Optional[Path] = None,
    palate_store: Optional[PalateStore] = None,
    vcf: Optional[dict] = None,
    vcf_dir: Optional[Path] = None,
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

    if compound is None:
        croot = Path(compound_dir or os.environ.get("CULIN_COMPOUND", DEFAULT_COMPOUND))
        if (croot / "neighbors.jsonl").exists():
            compound = load_compound_tables(croot)
        else:
            compound = {"neighbors": [], "meta": {}, "_dir": str(croot.resolve())}
    else:
        compound.setdefault("_dir", "memory")

    if vcf is None:
        vroot = Path(vcf_dir or os.environ.get("CULIN_VCF", DEFAULT_VCF))
        vcf = load_vcf_tables(vroot) if (vroot / "spine.jsonl").exists() else empty_vcf_tables(vroot)

    co_idx = index_cooccur(artifacts["cooccur"])
    tech_idx = index_techniques(artifacts["ingredient_technique"])
    compound_idx = index_neighbors(compound["neighbors"])

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
            "compound_artifacts": compound.get("_dir"),
            "cooccur_edges": len(artifacts["cooccur"]),
            "compound_edges": len(compound["neighbors"]),
            "technique_edges": len(artifacts["ingredient_technique"]),
            "palate_db": palate_ok,
            "compound_source": COMPOUND_SOURCE,
            "vcf_artifacts": vcf.get("_dir"),
            "vcf": vcf.get("counts"),
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

    @app.get("/compound")
    def compound_neighbors(
        ingredient: str = Query(..., description="Focus ingredient (Foodb or common name)"),
        n: int = Query(24, ge=1, le=100),
    ):
        canon, results = top_compound_neighbors(
            compound["neighbors"],
            ingredient,
            n=n,
            index=compound_idx,
        )
        return {
            "ingredient": ingredient,
            "canonical": canon,
            "results": results,
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

    # ---------------------------------------------------------------- LLM --

    @app.post("/llm/chat")
    def llm_chat(body: LlmChatBody):
        """
        Proxy chat completions so the OpenAI key stays server-side (§2.9).

        As a VITE_ variable the key compiles into the browser bundle and is
        readable from the network tab of any hosted page. Localhost is fine;
        a demo link is not. The key is read from the process environment here
        and never leaves it.
        """
        import httpx

        key = os.environ.get("OPENAI_API_KEY") or os.environ.get("VITE_OPENAI_API_KEY")
        if not key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is not set on the API process. Export it before `npm run api`.",
            )

        payload: dict[str, Any] = {
            k: v for k, v in body.model_dump().items() if v is not None
        }
        payload.setdefault(
            "model", os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        )

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"upstream error: {exc}") from exc

        if res.status_code >= 400:
            # Pass the upstream status through, but not the key or headers.
            raise HTTPException(status_code=res.status_code, detail=res.text[:400])
        return res.json()

    @app.get("/llm/status")
    def llm_status():
        """Whether the proxy can serve — the browser must never see the key itself."""
        return {
            "configured": bool(
                os.environ.get("OPENAI_API_KEY") or os.environ.get("VITE_OPENAI_API_KEY")
            ),
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        }

    # ---------------------------------------------------------------- VCF --

    def _culinary_members(entry: dict) -> list[dict]:
        return [m for m in (entry.get("members") or []) if m.get("class") == "culinary"]

    @app.get("/vcf/spine")
    def vcf_spine(spine_id: str = Query(...)):
        entry = vcf["spine_by_id"].get(spine_id)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"no spine entry {spine_id}")
        return entry

    @app.get("/vcf/pairs")
    def vcf_pairs(
        spine_id: str = Query(..., description="anchor spine id, e.g. culin:coffee"),
        n: int = Query(24, ge=1, le=200),
    ):
        """
        Shared-compound neighbours for one spine entry.

        Returns the compounds, not just the score: a chef cannot verify 0.211,
        but "they share pyrroles and pyrazines" is evidence they can act on.
        """
        rows = vcf["pairs_by_spine"].get(spine_id, [])[:n]
        return {
            "spine_id": spine_id,
            "source": "pairs",
            "count": len(rows),
            "results": rows,
        }

    @app.get("/vcf/forms")
    def vcf_forms(spine_id: str = Query(...), n: int = Query(24, ge=1, le=200)):
        """
        Form diffs for one spine entry, plus an explicit coverage state.

        A lens must be able to say "one known culinary form" and "not in the
        corpus" differently — absence of diff rows means both, and inferring
        which from the absence is exactly the guess this endpoint removes.
        """
        entry = vcf["spine_by_id"].get(spine_id)
        if entry is None:
            return {"spine_id": spine_id, "coverage": "not_in_corpus", "count": 0, "results": []}
        n_culinary = len(_culinary_members(entry))
        if n_culinary == 0:
            coverage = "not_in_corpus"
        elif n_culinary == 1:
            coverage = "single_form"
        else:
            coverage = "multi_form"
        rows = vcf["forms_by_spine"].get(spine_id, [])[:n]
        return {
            "spine_id": spine_id,
            "coverage": coverage,
            "n_culinary_members": n_culinary,
            "count": len(rows),
            "results": rows,
        }

    @app.get("/vcf/phase")
    def vcf_phase(
        product_id: int = Query(..., description="vcf_product_id of one plate component"),
        against: Optional[int] = Query(None, description="optional second product id"),
        n: int = Query(24, ge=1, le=200),
    ):
        """
        Phase-behaviour rows for a product, with the authored sentence attached
        where one fires.

        render_mode is the contract: "framed" rows carry a sentence authored in
        phase_frames.jsonl and it is rendered verbatim; "data_only" rows carry
        shares and percentiles and nothing else. There is deliberately no
        fallback sentence for data_only — a generic default would satisfy the
        letter of "no sentence outside phase_frames.jsonl" while doing the exact
        damage that rule exists to prevent, leaving the chef an alert they
        cannot interpret and teaching them to dismiss the category.
        """
        rows = vcf["competition_by_product"].get(product_id, [])
        if against is not None:
            rows = [
                r for r in rows
                if against in (r.get("vcf_product_id_a"), r.get("vcf_product_id_b"))
            ]
        frames = {f["frame_id"]: f for f in vcf["phase_frames"]}
        out = []
        for r in rows[:n]:
            row = dict(r)
            frame = frames.get(r.get("frame_id")) if r.get("frame_id") else None
            row["sentence"] = frame["sentence"] if frame else None
            out.append(row)
        return {
            "product_id": product_id,
            "count": len(out),
            "n_framed": sum(1 for r in out if r.get("sentence")),
            "results": out,
        }

    @app.get("/vcf/meta")
    def vcf_meta():
        return {"counts": vcf.get("counts"), "dir": vcf.get("_dir"), "meta": vcf.get("meta") or {}}

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
