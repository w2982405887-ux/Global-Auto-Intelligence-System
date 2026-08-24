from pathlib import Path

root = Path(__file__).resolve().parents[2]
texts = "\n".join(p.read_text(encoding="utf-8") for p in (root / "database/migrations").glob("*.sql"))
for marker in [
    "CREATE TABLE IF NOT EXISTS customs.vehicle_tariff_rate_line",
    "CREATE TABLE IF NOT EXISTS rules.automotive_incentive_program",
    "CREATE TABLE IF NOT EXISTS rules.vehicle_tax_route",
]:
    start = texts.find(marker)
    print(f"--- {marker} ---")
    if start < 0:
        print("NOT FOUND")
        continue
    end = texts.find(");", start) + 2
    print(texts[start:end])
