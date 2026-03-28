# IEC CIM Energy Ontology Module

**Module key**: `iec-cim` | **Standard**: IEC 61970/61968 Common Information Model | **Authority**: IEC TC57

---

## What is IEC CIM?

The **IEC Common Information Model (CIM)** is the international standard (IEC 61970/61968) for
representing power system assets, energy markets, and grid operations. It is the lingua franca for
utilities and grid operators (TSOs, DSOs) exchanging data across SCADA, EMS, and market systems.

---

## Key Classes Used in USF

| Class | CURIE | CIM Package | Description |
|-------|-------|-------------|-------------|
| Substation | `cim:Substation` | Core | High-voltage substation |
| ACLineSegment | `cim:ACLineSegment` | Wires | AC transmission line segment |
| EnergyConsumer | `cim:EnergyConsumer` | Wires | Load point / consumer |
| GeneratingUnit | `cim:GeneratingUnit` | Generation | Generating plant unit |
| ConformLoad | `cim:ConformLoad` | LoadModel | Typical load group |
| MeasurementValue | `cim:MeasurementValue` | Meas | Sensor or meter reading |
| EnergySchedulingType | `cim:EnergySchedulingType` | EnergyArea | Market scheduling type |
| ControlArea | `cim:ControlArea` | ControlArea | Grid control area (TSO zone) |

---

## Key Properties

| Property | CURIE | Description |
|----------|-------|-------------|
| `cim:name` | `cim:IdentifiedObject.name` | Human-readable name |
| `cim:mRID` | `cim:IdentifiedObject.mRID` | UUID master resource ID |
| `cim:nominalVoltage` | `cim:BaseVoltage.nominalVoltage` | Voltage level (kV) |
| `cim:p` | `cim:EnergyConsumer.p` | Active power consumption (MW) |
| `cim:q` | `cim:EnergyConsumer.q` | Reactive power (MVAr) |
| `cim:value` | `cim:MeasurementValue.value` | Sensor reading |
| `cim:timeStamp` | `cim:MeasurementValue.timeStamp` | Reading timestamp |

---

## Quick Start

### 1. Schema Detection

USF detects energy data from column names or table names including `mrid`, `nominal_voltage`,
`active_power_mw`, `substation_id`, or `control_area`.

### 2. Column Mapping for Common Datasets

#### ENTSO-E Transparency Platform (generation, load)

| ENTSO-E Column | CIM Class | SDL Entity |
|----------------|-----------|------------|
| `AreaCode` | `cim:ControlArea` | `ControlArea` |
| `ProductionType` | `cim:GeneratingUnit` | `GeneratingUnit` |
| `ActualGenerationOutput` | `cim:MeasurementValue.value` | `GenerationReading` |
| `ActualLoad` | `cim:EnergyConsumer.p` | `LoadReading` |
| `DateTime` | `cim:MeasurementValue.timeStamp` | `GenerationReading.timestamp` |

#### SCADA Time-Series (PI Historian / OSIsoft)

| PI Tag | CIM Mapping | Units |
|--------|-------------|-------|
| `SUB_001_V_kV` | `cim:BaseVoltage.nominalVoltage` | kV |
| `GEN_002_P_MW` | `cim:GeneratingUnit.normalPF` | MW |
| `LINE_003_I_A` | `cim:ACLineSegment.currentFlow` | A |

---

## Regulatory and Industry Use Cases

### ENTSO-E Network Codes (EU Grid)

Map `ControlArea` entities to bidding zones for capacity calculation.
Use the `cim:controlAreaSolution` relationship for cross-border flows.

### IEC 61968-9 Meter Reading (AMI)

Ingest AMI meter reads via CSV: map meter serial → `cim:Meter.serialNumber`,
readings → `cim:MeterReading.value` with `cim:readingType` = energy (kWh).

### Carbon Intensity Reporting (Scope 2)

Join `GeneratingUnit` (production_type=renewables) with `MeasurementValue`
to compute hourly carbon intensity per `ControlArea`.

---

## CIM Namespace Prefixes

```turtle
@prefix cim:  <http://iec.ch/TC57/2013/CIM-schema-cim16#> .
@prefix entsoe: <http://entsoe.eu/CIM/SchemaExtension/3/1#> .
@prefix md:   <http://iec.ch/TC57/61970-552/ModelDescription/1#> .
```
