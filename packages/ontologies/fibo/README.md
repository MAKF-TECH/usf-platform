# FIBO Industry Bridge for USF

## What is FIBO?

The **Financial Industry Business Ontology (FIBO)** is a formal ontology developed by the [EDM Council](https://edmcouncil.org/page/aboutfibo), published as OWL 2. It covers the full semantic model of financial services: legal entities, financial products, transactions, contracts, currencies, and more.

FIBO IRIs are hosted at `https://spec.edmcouncil.org/fibo/ontology/`.

## How USF Uses FIBO

USF uses FIBO as the **default ontology module** for the banking/financial services pilot. Specifically:

1. **SHACL shapes** (`shacl/`) — validate that ingested triples conform to FIBO class definitions
2. **SDL starter** (`sdl/banking_starter.yaml`) — pre-built entity definitions mapped to FIBO IRIs
3. **Few-shot examples** (`few_shot/`) — guide LangExtract to extract FIBO-typed entities from text
4. **Column mappings** (`mappings/`) — map Kaggle dataset columns to FIBO properties

## Key FIBO Classes Used

| USF Label | FIBO IRI |
|-----------|---------|
| Account | `https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Account` |
| LegalEntity | `https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/LegalEntity` |
| CommercialBank | `https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialInstitutions/CommercialBank` |
| FinancialTransaction | `https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/FinancialInstrument` |
| MonetaryAmount | `https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/CurrencyAmount/MonetaryAmount` |

## Loading Into USF

Load the FIBO SHACL shapes into the `usf-kg` service at startup:
```bash
POST /ontology/load
{
  "turtle_url": "https://raw.githubusercontent.com/MAKF-TECH/usf-platform/main/packages/ontologies/fibo/shacl/account.ttl",
  "named_graph": "usf://ontology/fibo/shacl/2024-Q4"
}
```
