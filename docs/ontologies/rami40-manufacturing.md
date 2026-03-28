# RAMI 4.0 Manufacturing Ontology Module

**Module key**: `rami40` | **Standard**: RAMI 4.0 / IEC 62890 / Asset Administration Shell | **Authority**: Platform Industrie 4.0 (Germany), IEC TC65

---

## What is RAMI 4.0?

The **Reference Architectural Model Industrie 4.0 (RAMI 4.0)** is the conceptual framework for
implementing Industry 4.0. It defines a three-dimensional reference model:

- **Layers**: Business → Functional → Information → Communication → Integration → Asset
- **Hierarchy levels**: Product → Field Device → Control Device → Station → Work Centre → Enterprise → Connected World
- **Life cycle**: Type (design) → Instance (production) → Decommission

The **Asset Administration Shell (AAS)** is the digital twin specification derived from RAMI 4.0.
USF maps AAS submodels and RAMI concepts to OWL for semantic querying across factory systems.

---

## Key Classes Used in USF

| Class | CURIE | RAMI / AAS Source | Description |
|-------|-------|-------------------|-------------|
| Asset | `rami:Asset` | AAS Part 1 | Physical or logical manufacturing asset |
| AssetAdminShell | `rami:AssetAdministrationShell` | AAS Part 1 | Digital twin shell |
| Submodel | `rami:Submodel` | AAS Part 2 | Functional aspect of an AAS |
| SubmodelElement | `rami:SubmodelElement` | AAS Part 2 | Property, operation, or event |
| ManufacturingProcess | `rami:ManufacturingProcess` | IEC 62890 | Production step |
| WorkOrder | `rami:WorkOrder` | MES integration | Manufacturing order |
| QualityMeasurement | `rami:QualityMeasurement` | ISO 9001 | QC measurement value |
| MachineState | `rami:MachineState` | OPC UA mapping | Operational state (running/idle/fault) |

---

## Key Properties

| Property | CURIE | Description |
|----------|-------|-------------|
| `rami:assetId` | `rami:Asset.assetId` | Global Asset ID (GAID) |
| `rami:serialNumber` | `rami:Asset.serialNumber` | Physical serial number |
| `rami:hasSubmodel` | `rami:AssetAdminShell.submodel` | Link AAS → Submodel |
| `rami:oeeValue` | `rami:KPI.oee` | Overall Equipment Effectiveness (0–1) |
| `rami:cycleTime` | `rami:ManufacturingProcess.cycleTime` | Process cycle time (seconds) |
| `rami:defectRate` | `rami:QualityMeasurement.defectRate` | Defect ratio |
| `rami:machineState` | `rami:MachineState.value` | running \| idle \| fault \| maintenance |
| `rami:timestamp` | `rami:Measurement.timestamp` | ISO 8601 timestamp |

---

## Quick Start

### 1. Schema Detection

USF detects manufacturing data from column names or table names including `asset_id`, `work_order`,
`oee`, `cycle_time`, `machine_state`, or `production_line`.

### 2. Column Mapping for Common Datasets

#### OPC UA Historical Data (UA NodeSet export)

| UA Node | RAMI Class | SDL Entity |
|---------|-----------|------------|
| `ns=2;s=Machine1.State` | `rami:MachineState` | `Machine` |
| `ns=2;s=Machine1.CycleTime` | `rami:ManufacturingProcess.cycleTime` | `Process` |
| `ns=2;s=Line1.OEE` | `rami:KPI.oee` | `ProductionLine` |
| `ns=2;s=QC.DefectCount` | `rami:QualityMeasurement` | `QualityCheck` |

#### SAP Production Orders (PP Module CSV export)

| SAP Field | RAMI Class | SDL Entity |
|-----------|-----------|------------|
| `AUFNR` | `rami:WorkOrder.id` | `WorkOrder.order_id` |
| `MATNR` | `rami:Asset.partNumber` | `Part.part_number` |
| `GAMNG` | `rami:ManufacturingProcess.quantity` | `WorkOrder.planned_qty` |
| `ISM01` | `rami:ManufacturingProcess.actualQty` | `WorkOrder.actual_qty` |
| `GSTRP` | `rami:WorkOrder.scheduledStart` | `WorkOrder.start_date` |

---

## Industry Use Cases

### OEE Monitoring (ISO 22400)

Define `oee_by_machine` metric:

```yaml
metrics:
  - name: oee_by_machine
    ontology_class: rami:KPI
    description: Overall Equipment Effectiveness per machine
    type: avg
    measure: oee_value
    measure_entity: Machine
    dimensions:
      - name: machine_name
        entity: Machine
        property: asset_name
        ontology_property: rami:assetId
    time_grains: [day, week, month]
    time_column: "m.reading_timestamp"
    time_entity: Machine
```

### Asset Administration Shell (AAS) Query

```sparql
PREFIX rami: <https://admin-shell.io/aas/3/0/>
SELECT ?shell ?submodel WHERE {
  ?shell a rami:AssetAdministrationShell ;
         rami:hasSubmodel ?submodel .
}
```

### ISO 9001 Quality Reporting

Map `defect_rate_by_product` metric to ISO 9001 Section 8.7 (Non-conforming outputs).
Use `clearance: confidential` for customer-specific defect data.

### ISA-95 MES Integration

RAMI 4.0 layers map directly to ISA-95 enterprise-to-control hierarchy:
- Level 4 (ERP) → `Enterprise` context
- Level 3 (MES) → `WorkCenter` context
- Level 2 (SCADA) → `Field` context

---

## RAMI 4.0 Namespace Prefixes

```turtle
@prefix rami:  <https://admin-shell.io/aas/3/0/> .
@prefix i40:   <https://www.plattform-i40.de/ontology/> .
@prefix opcua: <http://opcfoundation.org/UA/> .
@prefix isa95: <http://www.mesa.org/xml/B2MML-V0600/> .
```
