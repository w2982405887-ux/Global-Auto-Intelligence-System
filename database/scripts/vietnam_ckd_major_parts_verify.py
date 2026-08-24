from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


env = load_dotenv(PROJECT_ROOT / ".env")
url = (
    f"postgresql+psycopg://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}"
    f"@127.0.0.1:{env.get('POSTGRES_PORT', '5432')}/{env['POSTGRES_DB']}"
)
engine = create_engine(url)

queries = [
    (
        "mapping_count",
        """
        SELECT count(*)
        FROM customs.tariff_mapping
        WHERE tariff_version LIKE 'VN-%-2026-CKD-MAJOR-PARTS'
        """,
    ),
    (
        "by_agreement",
        """
        SELECT a.agreement_code, count(*) AS rows
        FROM customs.tariff_mapping m
        JOIN ref.trade_agreement a ON a.trade_agreement_id=m.trade_agreement_id
        WHERE m.tariff_version LIKE 'VN-%-2026-CKD-MAJOR-PARTS'
        GROUP BY a.agreement_code
        ORDER BY a.agreement_code
        """,
    ),
    (
        "component_count",
        """
        SELECT count(*)
        FROM customs.customs_classification_unit
        WHERE ccu_code LIKE 'VN-CKD-%'
        """,
    ),
]

with engine.begin() as conn:
    for name, sql in queries:
        print(name)
        for row in conn.execute(text(sql)):
            print(tuple(row))
