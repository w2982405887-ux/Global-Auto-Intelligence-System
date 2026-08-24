from __future__ import annotations

import csv
from pathlib import Path


IN = Path("database/reference_exports/vietnam_fta_8703_rates_extracted_round1.csv")
OUT = Path("database/reference_exports/vietnam_acfta_atiga_8703_cbu_rates_ready_round1.csv")


def main() -> int:
    csv.field_size_limit(10_000_000)
    rows = list(csv.DictReader(IN.open(encoding="utf-8-sig")))
    prepared = []
    for row in rows:
        if row["agreement"] not in {"ACFTA", "ATIGA"}:
            continue
        if row["business_scope_guess"] != "CBU_OR_ORDINARY_VEHICLE_BLOCK":
            continue
        if row["rate_column_count"] not in {"1", "6"}:
            continue
        if not row["national_tariff_code_as_stored"]:
            continue

        rates = row["rates_extracted"].split("|") if row["rates_extracted"] else []
        if row["agreement"] == "ATIGA":
            # Decree 126/2022 tables use six annual columns for 2022-2027.
            row["rate_2026"] = rates[4] if len(rates) >= 5 else ""
            row["rate_2027"] = rates[5] if len(rates) >= 6 else ""
        else:
            # ACFTA Decree 118/2022 attachment segment presents one rate column
            # for the 2022-2027 schedule in this extracted page range.
            row["rate_2026"] = rates[0] if len(rates) == 1 else ""
            row["rate_2027"] = rates[0] if len(rates) == 1 else ""
        prepared.append(row)

    fields = [
        "agreement",
        "source_file",
        "vn_code",
        "hs6_code",
        "national_tariff_code_as_stored",
        "description_vi",
        "rates_extracted",
        "rate_2026",
        "rate_2027",
        "country_markers",
        "business_scope_guess",
        "extraction_status",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{k: row.get(k, "") for k in fields} for row in prepared])
    print(f"wrote {OUT} rows={len(prepared)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
