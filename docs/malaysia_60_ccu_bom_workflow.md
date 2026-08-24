# Malaysia 60-CCU BOM comparison workflow

This input package separates public tariff data from enterprise use-time data.
It does not prefill a vehicle price, BOM quantity, customs value, final tariff
selection, origin qualification, excise conclusion or GRI 2(a) conclusion.

## Generate the package

```powershell
.\scripts\db-build-malaysia-60-ccu-bom-package.ps1
```

Generated files:

- `outputs/malaysia_60_ccu_bom_input_template.json`
- `outputs/malaysia_60_ccu_mapping_options.csv`
- `outputs/malaysia_60_ccu_bom_readiness.json`

## Use-time sequence

1. Copy the JSON template for one vehicle and one import date.
2. Set `included=true` only for CCUs actually present in the shipment.
3. Fill quantity and value. Unknown values stay `null`, never zero.
4. Select one explicit mapping code for every requested regime.
5. Attach enterprise technical evidence before setting
   `enterprise_inputs_complete=true`.
6. Complete shipment-level GRI 2(a) review.
7. Confirm FTA proof and product-specific origin rules. A portal rate alone is
   not proof of eligibility.
8. Fill sales revenue and non-import costs if profit comparison is required.
9. Submit only a complete, validated payload to the deterministic engine.

Compile and validate:

```powershell
.\scripts\db-compile-malaysia-60-ccu-bom.ps1
```

The command always writes
`outputs/malaysia_60_ccu_bom_validation.json`. It writes
`outputs/malaysia_60_ccu_calculation_request.json` only when every blocking
input is complete. Always check that the validation report says
`calculation_ready=true` before using a request file from an earlier run.

## Safety behavior

- Multiple candidates are preserved.
- Missing rates or source clauses block calculation.
- Missing FTA qualification falls back to MFN only when explicitly allowed.
- Candidate mappings remain visibly partial even when a numerical comparison is
  possible.
- Missing enterprise values are not written into the database as invented
  defaults.
