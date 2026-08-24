from __future__ import annotations

import csv
import re
from pathlib import Path


EXTRACT_DIR = Path(".tmp/vn_fta_extract")
OUT = Path("database/reference_exports/vietnam_fta_8703_worklist_round1.csv")


def agreement_for(name: str) -> str:
    if "118-2022" in name:
        return "ACFTA"
    if "126-2022" in name:
        return "ATIGA"
    if "129-2022" in name:
        return "RCEP"
    return "UNKNOWN"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    code_pat = re.compile(r"\b(8703\.\d{2}\.\d{2})\b")
    for path in sorted(EXTRACT_DIR.glob("*_8703.txt")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        agreement = agreement_for(path.name)
        for match in code_pat.finditer(text):
            code = match.group(1)
            start = max(0, match.start() - 200)
            end = min(len(text), match.end() + 400)
            context = re.sub(r"\s+", " ", text[start:end]).strip()
            rows.append(
                {
                    "agreement": agreement,
                    "source_extract_file": path.name,
                    "vn_hs8_code": code,
                    "national_tariff_code_as_stored": code.replace(".", "") + "00",
                    "hs6_code": code.replace(".", "")[:6],
                    "extraction_status": "HS_CODE_FOUND_RATE_NEEDS_TABLE_EXTRACTION",
                    "preferential_rate": "",
                    "rate_year_columns": "",
                    "context_snippet": context[:900],
                }
            )

    dedup: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["agreement"], row["source_extract_file"], row["vn_hs8_code"])
        dedup.setdefault(key, row)

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "agreement",
                "source_extract_file",
                "vn_hs8_code",
                "national_tariff_code_as_stored",
                "hs6_code",
                "extraction_status",
                "preferential_rate",
                "rate_year_columns",
                "context_snippet",
            ],
        )
        writer.writeheader()
        writer.writerows(dedup.values())

    print(f"wrote {OUT} rows={len(dedup)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
