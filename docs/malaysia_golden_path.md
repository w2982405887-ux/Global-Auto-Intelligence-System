# Malaysia Phase 1.4 Golden Path

## Purpose

This golden path proves that the current database layers can execute and retain
an auditable Malaysia calculation:

`scenario input -> eligibility gate -> tariff mapping -> tax calculation -> fallback -> decision trace -> missing data -> LLM-safe view`

It uses a synthetic BEV CKD parts shipment containing the first ten CCUs and a
total customs value of MYR 100,000.

The records are marked `DEMO`. They are not a customs declaration, FTA
qualification, legal excise conclusion or real enterprise BOM.

## Run order

From the project root:

```powershell
.\scripts\db-migrate-demo-snapshot-gate.ps1
.\scripts\db-seed-malaysia-golden-path.ps1
.\scripts\db-run-malaysia-golden-path.ps1
.\scripts\db-verify-malaysia-golden-path.ps1
```

The scripts are idempotent.

## Demonstrated cases

1. MFN baseline.
2. ACFTA requested without enterprise origin evidence; fallback to MFN.
3. RCEP requested without enterprise origin evidence; fallback to MFN.
4. ACFTA eligibility simulation.
5. RCEP eligibility simulation.

The eligible simulations validate engine behaviour only. They do not establish
eligibility for a real shipment.

## DEMO snapshot gate

Production snapshots still require all use-time enterprise CCU inputs.

An incomplete snapshot bypasses the production gate only when all of these are
true:

- scenario code starts with `DEMO-`;
- scenario and snapshot payloads contain `demo_only=true`;
- both contain `enterprise_ccu_fields_complete=false`;
- both contain `operational_use_permitted=false`.

All golden-path runs remain `PARTIAL`. Open enterprise fields and GRI 2(a)
review are retained in `audit.missing_data`.

## Current calculation boundary

- Duty: selected `customs.tariff_mapping`.
- SST base: customs value + import duty + explicit excise assessment.
- SST rate: 10% portal rate captured in the current first-ten-CCU mappings.
- Excise: explicit zero demo input. This is not recorded as a legal exemption.
- Preferential qualification: blocked unless the demo proof and origin-rule
  gates are both true.
- Candidate classifications remain candidate and require human review.

## Acceptance criteria

The verification script must report:

- 5 runs;
- 30 calculation lines per run;
- 10 CCUs per run;
- 7 decision trace steps per run;
- 3 LLM-safe view items per run;
- MYR 100,000 base per run;
- run total equal to calculation-line total;
- both failed FTA cases falling back to MFN.
