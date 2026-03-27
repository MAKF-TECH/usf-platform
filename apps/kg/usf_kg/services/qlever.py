"""QLever SPARQL service for usf-kg."""
from __future__ import annotations

from loguru import logger
from usf_rdf import SPARQLClient, NamedGraphManager, Triple
from usf_rdf.triples import batch_to_sparql_update, _node_to_sparql
from rdflib import URIRef, Literal


class QLeverService:
    """High-level QLever operations for usf-kg."""

    def __init__(self, endpoint: str, update_endpoint: str) -> None:
        self.client = SPARQLClient(endpoint, update_endpoint)
        self.graphs = NamedGraphManager(self.client)

    async def start(self) -> None:
        await self.client.start()
        logger.info("QLeverService started")

    async def stop(self) -> None:
        await self.client.stop()

    async def insert_triples(self, graph_uri: str, triples: list[Triple]) -> int:
        """Insert triples into a named graph. Returns count inserted."""
        if not triples:
            return 0
        sparql = batch_to_sparql_update(triples, graph_uri)
        await self.client.update(sparql)
        logger.info("Triples inserted", graph=graph_uri, count=len(triples))
        return len(triples)

    async def list_graphs(self) -> list[str]:
        return await self.graphs.list_graphs()

    async def triple_count(self, graph_uri: str) -> int:
        return await self.graphs.triple_count(graph_uri)

    async def entity_detail(self, iri: str) -> dict:
        """Fetch all triples about an entity (subject) across all named graphs."""
        sparql = f"""
        SELECT ?g ?p ?o WHERE {{
            GRAPH ?g {{
                <{iri}> ?p ?o .
            }}
        }}
        """
        result = await self.client.query(sparql)
        bindings = self.client.bindings(result)

        # Fetch rdf:type
        type_sparql = f"""
        SELECT DISTINCT ?type WHERE {{
            GRAPH ?g {{
                <{iri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type .
            }}
        }}
        """
        type_result = await self.client.query(type_sparql)
        types = [row["type"] for row in self.client.bindings(type_result)]

        return {"iri": iri, "types": types, "properties": bindings}

    async def provenance_chain(self, iri: str) -> list[dict]:
        """Query PROV-O chain for an entity from provenance named graphs."""
        sparql = f"""
        PREFIX prov: <http://www.w3.org/ns/prov#>
        SELECT ?activity ?agent ?time ?source WHERE {{
            GRAPH ?g {{
                <{iri}> prov:wasGeneratedBy ?activity .
                OPTIONAL {{ ?activity prov:wasAssociatedWith ?agent }}
                OPTIONAL {{ ?activity prov:endedAtTime ?time }}
                OPTIONAL {{ ?activity prov:used ?source }}
            }}
        }}
        """
        result = await self.client.query(sparql)
        return self.client.bindings(result)
