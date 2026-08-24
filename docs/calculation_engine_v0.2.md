# Deterministic Tax and Profit Comparison Engine v0.2

## Decision objective

The engine compares import regimes by:

- gross and net import tax;
- effective tax rate;
- landed cost;
- total cost;
- gross profit and gross-profit margin;
- tax saving and profit uplift versus MFN.

It is decision support. It does not issue a final HS classification, customs
ruling, FTA qualification or legal tax opinion.

## Accuracy controls

- Every duty rate must come from an effective, `ACTIVE` tariff mapping.
- Every selected rate must link to a source clause.
- Every CCU and regime requires an explicit mapping code.
- Multiple candidate mappings are returned to the caller; the engine does not
  silently choose one.
- A missing duty or SST rate blocks that scenario.
- A candidate mapping forces `PARTIAL` completeness.
- Missing origin evidence prevents FTA use and may trigger MFN fallback.
- A zero excise input is not treated as proof of legal exemption.
- Missing enterprise technical fields and GRI 2(a) review remain visible.

## Profit inputs

Tax can be calculated without finance inputs, but profit comparison requires:

- expected sales revenue;
- non-import costs;
- optional additional landed cost by CCU;
- recoverable SST fraction, where legally supported.

If revenue or non-import costs are absent, tax results remain available and the
profit result is marked incomplete.

## API

- `POST /calculations/malaysia/preview`: calculate without persistence.
- `POST /calculations/malaysia/run`: calculate and save input snapshot,
  calculation lines, decision trace, missing data and LLM-safe view.

Both endpoints require explicit `selected_mapping_codes` for each CCU.

Run the local backend:

```powershell
.\scripts\backend-run.ps1
```

Interactive API documentation is then available at:

`http://127.0.0.1:8000/docs`

## Validation commands

```powershell
python -m pytest -q
.\scripts\db-reconcile-malaysia-python-engine.ps1
python .\scripts\smoke_test_malaysia_persistence.py
.\scripts\db-verify-tariff-update-readiness.ps1
```

The persistence smoke test rolls back its transaction after checking the
created records.

## Update discipline

New tariff or policy versions must be inserted as new effective-dated records.
Old versions must not be overwritten. Before a management comparison, run the
update-readiness query to identify:

- expired or soon-expiring sources;
- missing source hashes or archives;
- verified-but-unpublished mappings;
- candidate classifications;
- nomenclature correlations requiring confirmation;
- unresolved P0 gaps.
