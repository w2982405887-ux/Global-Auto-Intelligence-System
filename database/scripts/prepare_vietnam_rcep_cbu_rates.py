from __future__ import annotations

import csv
from pathlib import Path


IN = Path("database/reference_exports/vietnam_fta_8703_rates_extracted_round1.csv")
OUT = Path("database/reference_exports/vietnam_rcep_8703_cbu_rates_ready_round1.csv")


# Decree 129/2022/ND-CP Article 3: Annex A-F are ASEAN, Australia, China,
# Japan, Korea, New Zealand. The downloaded Official Gazette .doc files are
# page-pair chunks in the same order.
ORIGIN_GROUP_BY_FILE = {
    "2023_129 + 130_129-2022-NĐ-CP.doc": "ASEAN",
    "2023_147 + 148_129-2022-NĐ-CP.doc": "AU",
    "2023_163 + 164_129-2022-NĐ-CP.doc": "CN",
    "2023_179 + 180_129-2022-NĐ-CP.doc": "JP",
    "2023_181 + 182_129-2022-NĐ-CP.doc": "JP",
    "2023_197 + 198_129-2022-NĐ-CP.doc": "KR",
    "2023_213 + 214_129-2022-NĐ-CP.doc": "NZ",
    "2023_215 + 216_129-2022-NĐ-CP.doc": "NZ",
}

ORIGIN_COUNTRIES = {
    "ASEAN": "BN,KH,ID,LA,MY,SG,TH,MM,PH",
    "AU": "AU",
    "CN": "CN",
    "JP": "JP",
    "KR": "KR",
    "NZ": "NZ",
}


def main() -> int:
    csv.field_size_limit(10_000_000)
    rows = list(csv.DictReader(IN.open(encoding="utf-8-sig")))
    prepared = []
    seen: set[tuple[str, str]] = set()

    for row in rows:
        if row["agreement"] != "RCEP":
            continue
        origin_group = ORIGIN_GROUP_BY_FILE.get(row["source_file"])
        if not origin_group:
            continue
        if row["business_scope_guess"] != "CBU_OR_ORDINARY_VEHICLE_BLOCK":
            continue
        if row["rate_column_count"] != "6":
            continue
        if not row["national_tariff_code_as_stored"]:
            continue

        rates = row["rates_extracted"].split("|") if row["rates_extracted"] else []
        rate_2026 = rates[4] if len(rates) >= 5 else ""
        rate_2027 = rates[5] if len(rates) >= 6 else ""
        if not rate_2026 or rate_2026 == "*":
            continue

        key = (origin_group, row["national_tariff_code_as_stored"])
        if key in seen:
            continue
        seen.add(key)
        row["origin_group"] = origin_group
        row["origin_countries"] = ORIGIN_COUNTRIES[origin_group]
        row["rate_2026"] = rate_2026
        row["rate_2027"] = rate_2027
        prepared.append(row)

    fields = [
        "agreement",
        "origin_group",
        "origin_countries",
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
