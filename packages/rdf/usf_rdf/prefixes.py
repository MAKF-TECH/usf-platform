"""Standard RDF prefixes used across USF."""
from rdflib import Namespace

# Core W3C
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
SHACL = Namespace("http://www.w3.org/ns/shacl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DCTERMS = Namespace("http://purl.org/dc/terms/")

# Provenance
PROV = Namespace("http://www.w3.org/ns/prov#")

# FIBO namespaces
FIBO_BE_LE = Namespace(
    "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/"
)
FIBO_FBC_FI = Namespace(
    "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialInstitutions/"
)
FIBO_FBC_PS = Namespace(
    "https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/"
)
FIBO_FND_ACC = Namespace(
    "https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/CurrencyAmount/"
)
FIBO_SEC_SEC = Namespace(
    "https://spec.edmcouncil.org/fibo/ontology/SEC/Securities/Securities/"
)
FIBO_LOAN = Namespace(
    "https://spec.edmcouncil.org/fibo/ontology/LOAN/LoanContracts/LoanCore/"
)

# FHIR
FHIR = Namespace("http://hl7.org/fhir/")

# OpenLineage
OL = Namespace("https://openlineage.io/spec/1-0-5/OpenLineage.json#")

# USF internal
USF = Namespace("https://usf.makf.tech/ontology/")

# Prefix map for serialisation
PREFIXES: dict[str, str] = {
    "rdf": str(RDF),
    "rdfs": str(RDFS),
    "owl": str(OWL),
    "xsd": str(XSD),
    "sh": str(SHACL),
    "skos": str(SKOS),
    "dcterms": str(DCTERMS),
    "prov": str(PROV),
    "fibo-be-le": str(FIBO_BE_LE),
    "fibo-fbc-fi": str(FIBO_FBC_FI),
    "fibo-fbc-ps": str(FIBO_FBC_PS),
    "fibo-fnd-acc": str(FIBO_FND_ACC),
    "fibo-sec": str(FIBO_SEC_SEC),
    "fhir": str(FHIR),
    "usf": str(USF),
}
