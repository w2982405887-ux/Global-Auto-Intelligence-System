from __future__ import annotations

import csv
import os
import re
from pathlib import Path

import olefile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DOCS_ROOT = Path(
    os.environ.get(
        "GAIS_VIETNAM_FTA_DOCS_ROOT",
        str(PROJECT_ROOT / "database" / "reference_docs" / "vietnam_fta"),
    )
)
ACFTA_DOCS = REFERENCE_DOCS_ROOT / "china-asean"
ATIGA_DOCS = REFERENCE_DOCS_ROOT / "asean"
RCEP_DOCS = REFERENCE_DOCS_ROOT / "rcep"

SOURCES = [
    ("ACFTA", ACFTA_DOCS / "2023_545 + 546_118-2022-NĐ-CP.doc"),
    ("ATIGA", ATIGA_DOCS / "2023_475 + 476_126-2022-NĐ-CP.doc"),
    ("ATIGA", ATIGA_DOCS / "2023_477 + 478_126-2022-NĐ-CP.doc"),
    ("RCEP", RCEP_DOCS / "2023_129 + 130_129-2022-NĐ-CP.doc"),
    ("RCEP", RCEP_DOCS / "2023_147 + 148_129-2022-NĐ-CP.doc"),
    ("RCEP", RCEP_DOCS / "2023_163 + 164_129-2022-NĐ-CP.doc"),
    ("RCEP", RCEP_DOCS / "2023_179 + 180_129-2022-NĐ-CP.doc"),
    ("RCEP", RCEP_DOCS / "2023_181 + 182_129-2022-NĐ-CP.doc"),
    ("RCEP", RCEP_DOCS / "2023_197 + 198_129-2022-NĐ-CP.doc"),
    ("RCEP", RCEP_DOCS / "2023_213 + 214_129-2022-NĐ-CP.doc"),
    ("RCEP", RCEP_DOCS / "2023_215 + 216_129-2022-NĐ-CP.doc"),
]

OUT = PROJECT_ROOT / "database/reference_exports/vietnam_fta_8703_rates_extracted_round1.csv"
CODE_RE = re.compile(r"^8703\.\d{2}(?:\.\d{2})?$")
RATE_RE = re.compile(r"^(?:\d{1,3}|\*)$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}(?:,\s*[A-Z]{2})*$")


def read_worddocument_text(path: Path) -> str:
    with olefile.OleFileIO(str(path)) as ole:
        data = ole.openstream("WordDocument").read()
    return data.decode("utf-16le", errors="ignore")


def clean_cell(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.replace("\xa0", " ")).strip()


def likely_scope(code: str) -> str:
    if re.match(r"8703\.\d{2}\.[1-3]\d$", code):
        return "CKD_OR_SPECIAL_LOW_BLOCK"
    if re.match(r"8703\.(21|22|23|24|40|50|60|70|80|90)\.[4-9]\d$", code):
        return "CBU_OR_ORDINARY_VEHICLE_BLOCK"
    if re.match(r"8703\.\d{2}$", code):
        return "HEADING_OR_SUBHEADING"
    return "UNKNOWN"


def extract_rows(agreement: str, path: Path) -> list[dict[str, str]]:
    text = read_worddocument_text(path)
    cells = [clean_cell(c) for c in text.split("\x07")]
    rows: list[dict[str, str]] = []
    i = 0
    while i < len(cells):
        cell = cells[i]
        if not CODE_RE.match(cell):
            i += 1
            continue
        code = cell
        desc = cells[i + 1] if i + 1 < len(cells) else ""
        j = i + 2
        rates: list[str] = []
        countries: list[str] = []
        notes: list[str] = []
        while j < len(cells) and not CODE_RE.match(cells[j]):
            c = cells[j]
            if not c:
                j += 1
                continue
            if RATE_RE.match(c):
                rates.append(c)
            elif COUNTRY_RE.match(c):
                countries.append(c)
            elif c not in {"-", "–"}:
                notes.append(c)
            j += 1
        if code.startswith("8703."):
            padded = code.replace(".", "") + ("00" if len(code.replace(".", "")) == 8 else "")
            rows.append(
                {
                    "agreement": agreement,
                    "source_file": path.name,
                    "vn_code": code,
                    "hs6_code": code.replace(".", "")[:6],
                    "national_tariff_code_as_stored": padded if len(padded) == 10 else "",
                    "description_vi": desc,
                    "rates_extracted": "|".join(rates),
                    "country_markers": "|".join(countries),
                    "notes": "|".join(notes[:5]),
                    "business_scope_guess": likely_scope(code),
                    "rate_column_count": str(len(rates)),
                    "extraction_status": "EXTRACTED_FROM_WORDDOCUMENT_CELL_STREAM",
                }
            )
        i = max(j, i + 1)
    return rows


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, str]] = []
    for agreement, path in SOURCES:
        all_rows.extend(extract_rows(agreement, path))

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "agreement",
                "source_file",
                "vn_code",
                "hs6_code",
                "national_tariff_code_as_stored",
                "description_vi",
                "rates_extracted",
                "country_markers",
                "notes",
                "business_scope_guess",
                "rate_column_count",
                "extraction_status",
            ],
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"wrote {OUT} rows={len(all_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
