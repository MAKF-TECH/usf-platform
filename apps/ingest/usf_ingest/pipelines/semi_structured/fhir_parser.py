from __future__ import annotations

"""FHIR R4 JSON bundle parser.

Parses FHIR R4 JSON → typed Python objects via fhir.resources → RDF triples.
Triples are inserted into usf-kg via SPARQL UPDATE.
"""

import json
from pathlib import Path
from typing import Any

import httpx
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.observation import Observation
from loguru import logger
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from usf_ingest.config import get_settings

FHIR = Namespace("http://hl7.org/fhir/")
USF = Namespace("https://usf.platform/ontology/")
SNOMED = Namespace("http://snomed.info/sct/")


def parse_fhir_bundle(bundle_json: str | dict) -> Graph:
    """Parse a FHIR R4 JSON Bundle → rdflib Graph of triples."""
    g = Graph()
    g.bind("fhir", FHIR)
    g.bind("usf", USF)
    g.bind("xsd", XSD)

    if isinstance(bundle_json, str):
        raw = json.loads(bundle_json)
    else:
        raw = bundle_json

    bundle = Bundle.model_validate(raw)
    entries = bundle.entry or []

    for entry in entries:
        if not entry.resource:
            continue
        resource = entry.resource
        resource_type = resource.resource_type

        if resource_type == "Patient":
            _patient_to_rdf(resource, g)
        elif resource_type == "Observation":
            _observation_to_rdf(resource, g)
        else:
            # Generic resource: emit basic type triple
            res_id = getattr(resource, "id", None)
            if res_id:
                subj = USF[f"{resource_type}/{res_id}"]
                g.add((subj, RDF.type, FHIR[resource_type]))

    logger.info(f"FHIR bundle → {len(g)} RDF triples")
    return g


def _patient_to_rdf(patient: Patient, g: Graph) -> None:
    subj = USF[f"Patient/{patient.id}"]
    g.add((subj, RDF.type, FHIR.Patient))
    if patient.birthDate:
        g.add((subj, FHIR.birthDate, Literal(str(patient.birthDate), datatype=XSD.date)))
    if patient.name:
        for name in patient.name:
            given = " ".join(name.given or [])
            family = name.family or ""
            g.add((subj, FHIR.name, Literal(f"{given} {family}".strip())))


def _observation_to_rdf(obs: Observation, g: Graph) -> None:
    subj = USF[f"Observation/{obs.id}"]
    g.add((subj, RDF.type, FHIR.Observation))
    g.add((subj, FHIR.status, Literal(obs.status)))
    if obs.subject and obs.subject.reference:
        g.add((subj, FHIR.subject, USF[obs.subject.reference.replace("#", "")]))
    if obs.valueQuantity:
        vq = obs.valueQuantity
        g.add((subj, FHIR.valueQuantity, Literal(vq.value, datatype=XSD.decimal)))


async def insert_fhir_graph(
    graph: Graph,
    named_graph_uri: str,
) -> None:
    """Insert parsed FHIR triples into the USF KG via SPARQL UPDATE."""
    settings = get_settings()
    turtle = graph.serialize(format="turtle")
    sparql_update = f"""
INSERT DATA {{
  GRAPH <{named_graph_uri}> {{
    {turtle}
  }}
}}
"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.USF_KG_URL}/update",
            data=sparql_update,
            headers={"Content-Type": "application/sparql-update"},
        )
        response.raise_for_status()
    logger.info(
        "Inserted FHIR triples into KG",
        extra={"named_graph": named_graph_uri, "triples": len(graph)},
    )
