from __future__ import annotations
import hashlib, json
from typing import Any
from loguru import logger
from openai import AsyncOpenAI
from usf_query.config import settings
from usf_query.models import Hyperedge
from usf_query.services.arcadedb_client import ArcadeDBClient


def _he_id(triples: list) -> str:
    return "he_" + hashlib.sha256(json.dumps(sorted(triples)).encode()).hexdigest()[:8]


def _cluster(rows: list[dict[str, Any]], cls_map: dict[str, str]) -> list[Hyperedge]:
    groups: dict[str, list] = {}
    ents: dict[str, set] = {}
    for row in rows:
        s = str(row.get("s", row.get("@rid", "")))
        p = str(row.get("p", row.get("type", "")))
        o = str(row.get("o", row.get("value", "")))
        cls = cls_map.get(s, "owl:Thing")
        groups.setdefault(cls, []).append((s, p, o))
        ents.setdefault(cls, set()).add(s)
    return [Hyperedge(id=_he_id(t), ontology_class=c, triples=t, entities=list(ents[c]))
            for c, t in groups.items()]


async def ograg_retrieve(question: str, context: str, kg_client: ArcadeDBClient, k: int = 5, max_depth: int = 2) -> list[Hyperedge]:
    llm = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    # Step 1: extract entities
    r = await llm.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": f"Extract key entities as JSON array. Question: {question}\nReturn ONLY JSON array."}],
        temperature=0.0, max_tokens=256,
    )
    try:
        raw = r.choices[0].message.content or "[]"
        if "```" in raw:
            raw = raw.split("```")[1].strip()
        entities: list[str] = json.loads(raw)
    except Exception:
        entities = []

    # Step 2: subgraph retrieval
    all_rows: list[dict[str, Any]] = []
    for ent in entities[:5]:
        try:
            all_rows.extend(await kg_client.get_subgraph(ent, depth=max_depth))
        except Exception as exc:
            logger.warning("OG-RAG subgraph failed", entity=ent, error=str(exc))

    # Step 3: vector search
    try:
        emb = await llm.embeddings.create(model="text-embedding-3-small", input=question)
        vec_rows = await kg_client.vector_search(f"usf_{context}_embeddings", emb.data[0].embedding, k=k * 2)
        all_rows.extend(vec_rows)
    except Exception as exc:
        logger.warning("OG-RAG vector search failed", error=str(exc))

    if not all_rows:
        return []

    cls_map = {row["@rid"]: row["type"] for row in all_rows if "@rid" in row and "type" in row}
    hyperedges = _cluster(all_rows, cls_map)
    if not hyperedges:
        return []

    # Step 4: score
    summary = [{"id": h.id, "class": h.ontology_class, "entities": h.entities[:3]} for h in hyperedges]
    try:
        sr = await llm.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": f"Score relevance (0-1) of these hyperedges for: {question}\n{json.dumps(summary)}\nReturn JSON: [{{\"id\": ..., \"score\": ...}}]"}],
            temperature=0.0, max_tokens=512,
        )
        raw_scores = sr.choices[0].message.content or "[]"
        if "```" in raw_scores:
            raw_scores = raw_scores.split("```")[1].strip()
        scores = {s["id"]: float(s.get("score", 0)) for s in json.loads(raw_scores)}
        for h in hyperedges:
            h.relevance_score = scores.get(h.id, 0.0)
    except Exception as exc:
        logger.warning("OG-RAG scoring failed", error=str(exc))

    hyperedges.sort(key=lambda h: h.relevance_score, reverse=True)
    return hyperedges[:k]
