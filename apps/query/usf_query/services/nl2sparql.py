from __future__ import annotations
import re
from loguru import logger
from openai import AsyncOpenAI
from usf_query.config import settings
from usf_query.models import QueryResult, QueryType, SemanticQuery

try:
    from rdflib.plugins.sparql import prepareQuery as rdflib_prepare
    HAS_RDFLIB = True
except ImportError:
    HAS_RDFLIB = False

_SYSTEM_PROMPT = (
    "You are a SPARQL 1.1 expert. Generate valid SPARQL from the user question and ontology schema.\n"
    "Rules:\n"
    "1. Use only classes/properties from the schema\n"
    "2. Declare all PREFIX statements\n"
    "3. Return ONLY the SPARQL query, no explanation\n"
    "4. Add LIMIT 1000 unless user requests all"
)


def _extract_sparql(text: str) -> str:
    m = re.search(r"```(?:sparql)?\s*((?:PREFIX|SELECT|CONSTRUCT|ASK|DESCRIBE).*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"((?:PREFIX\s+\S+:\s*<[^>]+>\s*)*(?:SELECT|CONSTRUCT|ASK|DESCRIBE)\b.*)", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else text.strip()


def _validate(sparql: str) -> tuple[bool, str]:
    if not HAS_RDFLIB:
        return True, ""
    try:
        rdflib_prepare(sparql)
        return True, ""
    except Exception as exc:
        return False, str(exc)


class NL2SPARQLError(Exception):
    def __init__(self, question: str, last_error: str) -> None:
        super().__init__(f"Failed SPARQL generation for: {question}. Last: {last_error}")
        self.question = question
        self.last_error = last_error


async def nl_to_sparql(question: str, ontology_context: str, max_iterations: int | None = None) -> str:
    iters = max_iterations or settings.nl2sparql_max_iterations
    client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    last_error = ""
    for i in range(1, iters + 1):
        prompt = f"Ontology schema:\n{ontology_context}\n\nQuestion: {question}"
        if i > 1:
            prompt += f"\n\nPrevious SPARQL was invalid. Error: {last_error}\nPlease fix it."
        logger.info("NL2SPARQL iteration", n=i, question=question[:60])
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": _SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            temperature=0.0, max_tokens=1024,
        )
        sparql = _extract_sparql(resp.choices[0].message.content or "")
        valid, err = _validate(sparql)
        if valid:
            logger.info("NL2SPARQL success", iteration=i)
            return sparql
        last_error = err
        logger.warning("NL2SPARQL invalid SPARQL, retrying", error=err[:200])
    raise NL2SPARQLError(question=question, last_error=last_error)


async def execute_nl_query(question: str, ontology_context: str, context: str | None, tenant_id: str | None) -> QueryResult:
    from usf_query.services.query_router import route_query
    sparql = await nl_to_sparql(question, ontology_context)
    result = await route_query(SemanticQuery(query=sparql, query_type=QueryType.SPARQL, context=context, tenant_id=tenant_id))
    result.sparql_generated = sparql
    return result
