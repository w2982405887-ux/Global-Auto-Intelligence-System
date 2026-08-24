# Malaysia vehicle tax models

## Effective legal baseline

- Customs Duties Order 2025 / PDK 2025: effective 1 November 2025.
- Excise Duties Order 2025, P.U. (A) 389/2025: effective 1 November 2025.
- Imported-goods SST base: customs value plus import duty plus excise duty.
- CKD EV incentive end date: 31 December 2027, subject to qualifying project
  approval and exemption confirmation.

## CBU model

`customs.vehicle_tariff_line` contains 247 official JKDM national tariff lines
for passenger vehicles under heading 87.03:

- ICE gasoline: 39;
- ICE diesel: 30;
- HEV: 86;
- PHEV: 86;
- BEV: 6.

All stored lines have an MFN import rate, excise rate, SST rate, official portal
evidence and the Excise Duties Order source. Rate verification does not choose
the final line. Vehicle body type, drive type, displacement and parent-branch
review remain mandatory classification inputs.

## Local assembly model

The database separates three policy paths:

1. qualifying locally assembled BEV with project approval and tax-exemption
   confirmation;
2. PHEV customised project incentive;
3. ICE customised project incentive.

BEV benefits are executable only when the approval gate is satisfied. PHEV and
ICE public sources do not provide a universal reduction rate or localization
threshold, so their rate and threshold fields must come from the enterprise
project approval. Missing approval means statutory tax applies, not zero.

## AI and frontend access

Use these current-version views instead of granting broad table access:

- `ai.v_malaysia_vehicle_tax_lines_current`;
- `ai.v_malaysia_automotive_incentives_current`;
- `ai.v_malaysia_vehicle_scenarios_current`.

Historical and superseded records remain in the underlying versioned tables.

## Run and verify

```powershell
.\scripts\db-run-malaysia-vehicle-tax-models.ps1
```

This command is idempotent and runs migration, evidence-linked loading,
database assertions, calculation-DSL validation and regression tests.
