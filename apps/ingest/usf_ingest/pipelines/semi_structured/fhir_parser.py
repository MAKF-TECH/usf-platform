from __future__ import annotations

"""FHIR R4 JSON bundle parser → rdflib Graph → usf-kg."""

import json

import httpx
from fhir.resources.bundle import Bundle
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from loguru import logger
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from usf_ingest.config import get_settings

FHIR = Namespace("http://hl7.org/fhir/")
USF = Namespace("https://usf.platform/ontology/")


def parse_fhir_bundle(bundle_json: str | dict) -> Graph:
    g = Graph()
    g.bind("fhir", FHIR)
    g.bind("usf", USF)

    raw = json.loads(bundle_json) if isinstance(bundle_json, str) else bundle_json
    bundle = Bundle.model_validate(raw)

    for entry in bundle.entry or []:
        if not entry.resource:
            continue
        r = entry.resource
        rt = r.resource_type
        if rt == "Patient":
            _patient_to_rdf(r, g)
        elif rt == "Observation":
            _observation_to_rdf(r, g)
        else:
            if getattr(r, "id", None):
                g.add((USF[f"{rt}/{r.id}"], RDF.type, FHIR[rt]))

    logger.info(f"FHIR bundle → {len(g)} triples")
    return g


def _patient_to_rdf(patient: Patient, g: Graph) -> None:
    subj = USF[f"Patient/{patient.id}"]
    g.add((subj, RDF.type, FHIR.Patient))
    if patient.birthDate:
        g.add((subj, FHIR.birthDate, Literal(str(patient.birthDate), datatype=XSD.date)))
    for name in patient.name or []:
        given = " ".join(name.given or [])
        g.add((subj, FHIR.name, Literal(f"{given} {name.family or ''}".strip())))


def _observation_to_rdf(obs: Observation, g: Graph) -> None:
    subj = USF[f"Observation/{obs.id}"]
    g.add((subj, RDF.type, FHIR.Observation))
    g.add((subj, FHIR.status, Literal(obs.status)))
    if obs.subject and obs.subject.reference:
        g.add((subj, FHIR.subject, USF[obs.subject.reference.replace("#", "")]))
    if obs.valueQuantity:
        g.add((subj, FHIR.valueQuantity, Literal(obs.valueQuantity.value, datatype=XSD.decimal)))


async def insert_fhir_graph(graph: Graph, named_graph_uri: str) -> None:
    settings = get_settings()
    turtle = graph.serialize(format="turtle")
    sparql = f"INSERT DATA {{ GRAPH <{named_graph_uri}> {{ {turtle} }} }}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{settings.USF_KG_URL}/update", data=sparql, headers={"Content-Type": "application/sparql-update"})
        r.raise_for_status()
    logger.info("Inserted FHIR triples", extra={"named_graph": named_graph_uri, "triples": len(graph)})
