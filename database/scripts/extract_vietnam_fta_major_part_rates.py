from __future__ import annotations

import csv
import re
from pathlib import Path

import olefile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / "database/reference_exports/vietnam_fta_major_parts_rates_extracted_round1.csv"

SOURCES = [
    ("ACFTA", "CN", Path(r"C:\Users\w2982\Downloads\中国-东盟")),
    ("ATIGA", "ASEAN", Path(r"C:\Users\w2982\Downloads\东盟内部")),
    ("RCEP", "ASEAN", Path(r"C:\Users\w2982\Downloads\RCEP")),
    ("RCEP", "AU", Path(r"C:\Users\w2982\Downloads\RCEP")),
    ("RCEP", "CN", Path(r"C:\Users\w2982\Downloads\RCEP")),
    ("RCEP", "JP", Path(r"C:\Users\w2982\Downloads\RCEP")),
    ("RCEP", "KR", Path(r"C:\Users\w2982\Downloads\RCEP")),
    ("RCEP", "NZ", Path(r"C:\Users\w2982\Downloads\RCEP")),
]

# File blocks previously confirmed from official downloaded attachments.
SOURCE_FILE_FILTERS = {
    ("ACFTA", "CN"): ("118-2022-NĐ-CP.doc",),
    ("ATIGA", "ASEAN"): ("126-2022-NĐ-CP.doc",),
    ("RCEP", "ASEAN"): ("129 + 130_129-2022-NĐ-CP.doc",),
    ("RCEP", "AU"): ("147 + 148_129-2022-NĐ-CP.doc",),
    ("RCEP", "CN"): ("163 + 164_129-2022-NĐ-CP.doc",),
    ("RCEP", "JP"): ("179 + 180_129-2022-NĐ-CP.doc", "181 + 182_129-2022-NĐ-CP.doc"),
    ("RCEP", "KR"): ("197 + 198_129-2022-NĐ-CP.doc",),
    ("RCEP", "NZ"): ("213 + 214_129-2022-NĐ-CP.doc", "215 + 216_129-2022-NĐ-CP.doc"),
}

TARGET_HS6 = {
    "401110",  # tyres
    "681381",  # brake friction material
    "700711", "700721", "700910",  # glass/mirrors
    "732010", "732020",  # springs
    "840734", "840820", "840991", "840999",  # engines and engine parts
    "841330", "841381", "841520",  # pumps / HVAC
    "842123", "842131", "842132",  # filters / catalytic
    "850131", "850152", "850153", "850440", "850760",  # EV power parts
    "851110", "851130", "851140", "851150", "851220", "851230", "851240", "851829",
    "852721", "853120", "853710", "854430",
    "870710", "870821", "870829", "870830", "870840", "870850", "870870", "870880",
    "870892", "870893", "870894", "870895", "870899",
    "902920", "903289", "940120",
}

CODE_RE = re.compile(r"^\d{4}\.\d{2}(?:\.\d{2})?$")
RATE_RE = re.compile(r"^(?:\d{1,3}|\*)$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}(?:,\s*[A-Z]{2})*$")


def read_worddocument_text(path: Path) -> str:
    with olefile.OleFileIO(str(path)) as ole:
        data = ole.openstream("WordDocument").read()
    return data.decode("utf-16le", errors="ignore")


def clean_cell(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.replace("\xa0", " ")).strip()


def list_source_files(agreement: str, origin_group: str, folder: Path) -> list[Path]:
    suffixes = SOURCE_FILE_FILTERS[(agreement, origin_group)]
    files: list[Path] = []
    for path in folder.glob("*.doc"):
        if any(path.name.endswith(suffix) for suffix in suffixes):
            files.append(path)
    return sorted(files)


def select_2026_rate(rates: list[str]) -> tuple[str, str]:
    if not rates:
        return "", "NO_RATE_COLUMN"
    # Vietnam preferential schedules commonly publish 2022-2027 columns;
    # for 2026 use the fifth annual column. If only one rate exists, use it.
    if len(rates) >= 5:
        return rates[4], "COLUMN_5_AS_2026"
    if len(rates) == 1:
        return rates[0], "SINGLE_RATE_COLUMN"
    return rates[-1], "LAST_AVAILABLE_COLUMN_FALLBACK"


def extract_rows(agreement: str, origin_group: str, path: Path) -> list[dict[str, str]]:
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
        digits = code.replace(".", "")
        hs6 = digits[:6]
        if hs6 not in TARGET_HS6:
            i += 1
            continue
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
        selected, basis = select_2026_rate(rates)
        rows.append(
            {
                "agreement": agreement,
                "origin_group": origin_group,
                "source_file": path.name,
                "vn_code": code,
                "hs6_code": hs6,
                "national_tariff_code": digits,
                "description_vi": desc,
                "rates_extracted": "|".join(rates),
                "rate_2026_percent": selected,
                "rate_selection_basis": basis,
                "country_markers": "|".join(countries),
                "notes": "|".join(notes[:5]),
                "rate_column_count": str(len(rates)),
                "extraction_status": "EXTRACTED_FROM_WORDDOCUMENT_CELL_STREAM",
            }
        )
        i = max(j, i + 1)
    return rows


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, str]] = []
    for agreement, origin_group, folder in SOURCES:
        for path in list_source_files(agreement, origin_group, folder):
            all_rows.extend(extract_rows(agreement, origin_group, path))

    fieldnames = [
        "agreement",
        "origin_group",
        "source_file",
        "vn_code",
        "hs6_code",
        "national_tariff_code",
        "description_vi",
        "rates_extracted",
        "rate_2026_percent",
        "rate_selection_basis",
        "country_markers",
        "notes",
        "rate_column_count",
        "extraction_status",
    ]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"wrote {OUT} rows={len(all_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
