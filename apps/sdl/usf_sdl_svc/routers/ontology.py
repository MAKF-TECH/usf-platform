"""GET /ontology/{module} — browse loaded ontology classes/properties."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/ontology", tags=["ontology"])

# Static module catalog
_MODULES: dict[str, dict] = {
    "fibo": {
        "description": "Financial Industry Business Ontology (FIBO)",
        "version": "2024-Q4",
        "classes": [
            {
                "iri": "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/LegalEntity",
                "label": "LegalEntity",
            },
            {
                "iri": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialInstitutions/CommercialBank",
                "label": "CommercialBank",
            },
            {
                "iri": "https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Account",
                "label": "Account",
            },
            {
                "iri": "https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/CurrencyAmount/MonetaryAmount",
                "label": "MonetaryAmount",
            },
        ],
    },
    "fhir": {
        "description": "HL7 FHIR R4 Resources",
        "version": "4.0.1",
        "classes": [
            {"iri": "http://hl7.org/fhir/Patient", "label": "Patient"},
            {"iri": "http://hl7.org/fhir/Observation", "label": "Observation"},
            {"iri": "http://hl7.org/fhir/Encounter", "label": "Encounter"},
        ],
    },
}


class OntologyModuleOut(BaseModel):
    module: str
    description: str
    version: str
    class_count: int
    classes: list[dict]


@router.get("/{module}", response_model=OntologyModuleOut)
async def get_ontology_module(module: str):
    if module not in _MODULES:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module}' not found. Available: {list(_MODULES.keys())}",
        )
    data = _MODULES[module]
    return OntologyModuleOut(
        module=module,
        description=data["description"],
        version=data["version"],
        class_count=len(data["classes"]),
        classes=data["classes"],
    )
