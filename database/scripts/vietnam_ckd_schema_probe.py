from pathlib import Path

root = Path(__file__).resolve().parents[2]
text = (root / "database/migrations/0001_phase1_core.sql").read_text(encoding="utf-8")
for marker in [
    "CREATE TABLE customs.customs_classification_unit",
    "CREATE TABLE customs.ccu_candidate_hs",
    "CREATE TABLE customs.tariff_mapping",
]:
    start = text.index(marker)
    end = text.index(");", start) + 2
    print(text[start:end])
    print()
