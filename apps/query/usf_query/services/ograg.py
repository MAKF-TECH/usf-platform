from __future__ import annotations

import hashlib
import json
import textwrap
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from usf_query.config import settings
from usf_query.models import Hyperedge
from usf_query.services.arcadedb_client import ArcadeDBClient


def _build_entity_extraction_prompt(question: str) -> str:
    return textwrap.dedent(f"""
        Extract the key named entities from this question. Return a JSON array of strings.
        Question: {question}
        Return ONLY a JSON array, e.g. ["Deutsche Bank AG", "EUR", "Q1 2024"]
    """).strip()


def _build_hyperedge_scoring_prompt(question: str, hyperedges_json: str) -> str:
    return textwrap.dedent(f"""
        Score these knowledge graph hyperedges for relevance to the question.
        Return a JSON array of objects with "id" and "score" (0.0-1.0).
        
        Question: {question}
        
        Hyperedges:
        {hyperedges_json}
        
        Return ONLY JSON, e.g. [{{"id": "he_0", "score": 0.9}}, ...]
    """).strip()


def _build_hyperedge_id(triples: list[tuple[str, str, str]]) -> str:
    key = json.dumps(sorted(triples), sort_keys=True)
    return "he_" + hashlib.sha256(key.encode()).hexdigest()[:8]


def _cluster_triples_by_class(
    subgraph_rows: list[dict[str, Any]],
    ontology_class_map: dict[str, str],
) -> list[Hyperedge]:
    """Group triples into hyperedges by ontology class."""
    # Group by subject ontology class
    class_groups: dict[str, list[tuple[str, str, str]]] = {}
    entities_by_class: dict[str, set[str]] = {}

    for row in subgraph_rows:
        s = str(row.get("s", row.get("start", {}).get("@rid", "")))
        p = str(row.get("p", row.get("type", "")))
        o = str(row.get("o", row.get("value", "")))

        # Determine ontology class for subject
        cls = ontology_class_map.get(s, "owl:Thing")
        if cls not in class_groups:
            class_groups[cls] = []
            entities_by_class[cls] = set()

        class_groups[cls].append((s, p, o))
        entities_by_class[cls].add(s)

    hyperedges = []
    for cls, triples in class_groups.items():
        he = Hyperedge(
            id=_build_hyperedge_id(triples),
            ontology_class=cls,
            triples=triples,
            entities=list(entities_by_class[cls]),
            relevance_score=0.0,
        )
        hyperedges.append(he)

    return hyperedges


async def ograg_retrieve(
    question: str,
    context: str,
    kg_client: ArcadeDBClient,
    k: int = 5,
    max_depth: int = 2,
) -> list[Hyperedge]:
    """
    OG-RAG retrieval (simplified from arXiv:2412.15235):
    1. Extract key entities from question via LLM
    2. Retrieve entity subgraphs from ArcadeDB (Cypher traversal, depth=max_depth)
    3. Retrieve semantically similar entities via ArcadeDB vector index
    4. Build hyperedges: clusters of related triples grounded by ontology class
    5. Score hyperedges by relevance to question
    6. Return top-k hyperedges as LLM context
    """
    llm_client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    # Step 1: Extract key entities
    logger.info("OG-RAG: extracting entities", question=question[:80])
    entity_resp = await llm_client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "user", "content": _build_entity_extraction_prompt(question)}
        ],
        temperature=0.0,
        max_tokens=256,
    )
    try:
        raw_entities = entity_resp.choices[0].message.content or "[]"
        # Strip markdown code blocks if present
        if "```" in raw_entities:
            raw_entities = raw_entities.split("```")[1].strip()
        entities: list[str] = json.loads(raw_entities)
    except (json.JSONDecodeError, IndexError):
        entities = []
        logger.warning("OG-RAG: failed to parse entities, using empty list")

    logger.info("OG-RAG: entities extracted", entities=entities)

    # Step 2: Retrieve subgraphs for each entity
    all_rows: list[dict[str, Any]] = []
    for entity in entities[:5]:  # cap to 5 entities for performance
        try:
            rows = await kg_client.get_subgraph(entity, depth=max_depth)
            all_rows.extend(rows)
        except Exception as exc:
            logger.warning("OG-RAG: subgraph retrieval failed", entity=entity, error=str(exc))

    # Step 3: Vector similarity search (get embedding of question first)
    try:
        embed_resp = await llm_client.embeddings.create(
            model="text-embedding-3-small",
            input=question,
        )
        question_vector = embed_resp.data[0].embedding
        vector_rows = await kg_client.vector_search(
            index_name=f"usf_{context}_embeddings",
            vector=question_vector,
            k=k * 2,  # retrieve more then filter
        )
        # Merge with subgraph rows
        all_rows.extend(vector_rows)
    except Exception as exc:
        logger.warning("OG-RAG: vector search failed", error=str(exc))

    if not all_rows:
        logger.warning("OG-RAG: no subgraph data retrieved")
        return []

    # Step 4: Build hyperedges from subgraph rows
    # Simplified ontology class map — in production this comes from the KG metadata
    ontology_class_map: dict[str, str] = {}
    for row in all_rows:
        if "type" in row and "@rid" in row:
            ontology_class_map[row["@rid"]] = row["type"]

    hyperedges = _cluster_triples_by_class(all_rows, ontology_class_map)

    if not hyperedges:
        return []

    # Step 5: Score hyperedges by relevance
    hyperedges_summary = [
        {
            "id": he.id,
            "class": he.ontology_class,
            "entities": he.entities[:3],
            "triple_count": len(he.triples),
        }
        for he in hyperedges
    ]

    try:
        score_resp = await llm_client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "user",
                    "content": _build_hyperedge_scoring_prompt(
                        question, json.dumps(hyperedges_summary, indent=2)
                    ),
                }
            ],
            temperature=0.0,
            max_tokens=512,
        )
        scores_raw = score_resp.choices[0].message.content or "[]"
        if "```" in scores_raw:
            scores_raw = scores_raw.split("```")[1].strip()
        scores: list[dict[str, Any]] = json.loads(scores_raw)
        score_map = {s["id"]: float(s.get("score", 0.0)) for s in scores}
        for he in hyperedges:
            he.relevance_score = score_map.get(he.id, 0.0)
    except Exception as exc:
        logger.warning("OG-RAG: scoring failed, using uniform scores", error=str(exc))

    # Step 6: Return top-k by score
    hyperedges.sort(key=lambda h: h.relevance_score, reverse=True)
    top_k = hyperedges[:k]

    logger.info(
        "OG-RAG: retrieval complete",
        total_hyperedges=len(hyperedges),
        top_k=len(top_k),
        top_scores=[round(h.relevance_score, 3) for h in top_k],
    )

    return top_k
