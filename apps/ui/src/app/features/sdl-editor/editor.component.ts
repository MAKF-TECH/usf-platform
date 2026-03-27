import {
  Component, ChangeDetectionStrategy, signal, computed
} from '@angular/core';
import { UpperCasePipe } from '@angular/common';

@Component({
  selector: 'usf-sdl-editor',
  standalone: true,
  imports: [UpperCasePipe],
  templateUrl: './editor.component.html',
  styleUrl: './editor.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SdlEditorComponent {
  activePreviewTab = signal<'owl' | 'sql' | 'r2rml' | 'shacl'>('owl');
  previewTabs: Array<'owl' | 'sql' | 'r2rml' | 'shacl'> = ['owl', 'sql', 'r2rml', 'shacl'];

  sdlSource = signal(`# USF Semantic Definition Language
# Tenant: Acme Bank · Context: risk

context: risk
  ontology: FIBO-v3.2.1
  owner: Risk Team

metrics:
  total_exposure_by_counterparty:
    description: Total credit exposure grouped by counterparty
    type: SUM
    entity: fibo:CreditExposure
    dimension: fibo:Counterparty
    filter:
      sector: EU_FINANCIAL
    unit: EUR
    access:
      roles: [risk_analyst, auditor]

  aml_flagged_ratio:
    description: Ratio of AML-flagged transactions
    type: RATIO
    numerator:
      entity: fibo:Transaction
      filter: { flag: AML_SUSPICIOUS }
    denominator:
      entity: fibo:Transaction
    unit: percent

definitions:
  revenue: net_interest_income
  balance: current_book_value

sources:
  - type: warehouse
    connection: postgresql://acme-dw.neon.tech/prod
    schema: public
  - type: document
    path: /data/annual-report-2023.pdf
`);

  owlPreview = computed(() => `@prefix fibo: <https://spec.edmcouncil.org/fibo/ontology/> .
@prefix usf:  <https://usf.io/ontology/> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .

usf:total_exposure_by_counterparty a usf:Metric ;
  usf:aggregation "SUM" ;
  usf:entity fibo:CreditExposure ;
  usf:dimension fibo:Counterparty ;
  usf:unit "EUR" ;
  usf:context usf:risk .

usf:aml_flagged_ratio a usf:Metric ;
  usf:aggregation "RATIO" ;
  usf:context usf:risk .`);

  sqlPreview = computed(() => `-- Generated SQL for: total_exposure_by_counterparty
-- Context: risk | Backend: Wren + PostgreSQL

SELECT
  cp.counterparty_name,
  cp.sector,
  SUM(ce.exposure_amount) AS total_exposure_eur
FROM credit_exposures ce
JOIN counterparties cp ON ce.counterparty_id = cp.id
WHERE cp.sector = 'EU_FINANCIAL'
GROUP BY cp.counterparty_name, cp.sector
ORDER BY total_exposure_eur DESC;

-- Generated SQL for: aml_flagged_ratio
SELECT
  CAST(COUNT(CASE WHEN flag = 'AML_SUSPICIOUS' THEN 1 END) AS FLOAT)
  / NULLIF(COUNT(*), 0) AS aml_flagged_ratio
FROM transactions;`);

  r2rmlPreview = computed(() => `@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix fibo: <https://spec.edmcouncil.org/fibo/ontology/> .

<#CreditExposureMapping> a rr:TriplesMap ;
  rr:logicalTable [ rr:tableName "credit_exposures" ] ;
  rr:subjectMap [
    rr:template "fibo:exposure/{id}" ;
    rr:class fibo:CreditExposure
  ] ;
  rr:predicateObjectMap [
    rr:predicate fibo:hasCounterparty ;
    rr:objectMap [ rr:template "fibo:counterparty/{counterparty_id}" ]
  ] ;
  rr:predicateObjectMap [
    rr:predicate fibo:exposureAmount ;
    rr:objectMap [ rr:column "exposure_amount" ; rr:datatype xsd:decimal ]
  ] .`);

  shaclPreview = computed(() => `@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix fibo: <https://spec.edmcouncil.org/fibo/ontology/> .

usf:CreditExposureShape a sh:NodeShape ;
  sh:targetClass fibo:CreditExposure ;
  sh:property [
    sh:path fibo:exposureAmount ;
    sh:datatype xsd:decimal ;
    sh:minCount 1 ;
    sh:minExclusive 0 ;
  ] ;
  sh:property [
    sh:path fibo:hasCounterparty ;
    sh:class fibo:Counterparty ;
    sh:minCount 1 ;
  ] .`);

  getPreview(): string {
    switch (this.activePreviewTab()) {
      case 'owl': return this.owlPreview();
      case 'sql': return this.sqlPreview();
      case 'r2rml': return this.r2rmlPreview();
      case 'shacl': return this.shaclPreview();
    }
  }
}
