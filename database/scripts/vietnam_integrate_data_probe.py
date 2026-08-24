from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine, text

root = Path(__file__).resolve().parents[2]
env = {}
for line in (root / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
url = f"postgresql+psycopg://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@127.0.0.1:{env.get('POSTGRES_PORT','5432')}/{env['POSTGRES_DB']}"
engine = create_engine(url)

queries = {
    "vn_routes": """
        SELECT route_code, route_kind, import_mode::text, classification_granularity
        FROM rules.vehicle_tax_route r JOIN ref.country c ON c.country_id=r.country_id
        WHERE c.iso2='VN' ORDER BY route_code
    """,
    "vn_vehicle_lines": """
        SELECT origin_regime::text, coalesce(a.agreement_code,'MFN') agreement, powertrain::text, count(*)
        FROM customs.vehicle_tariff_rate_line l
        JOIN ref.country c ON c.country_id=l.country_id
        LEFT JOIN ref.trade_agreement a ON a.trade_agreement_id=l.trade_agreement_id
        WHERE c.iso2='VN'
        GROUP BY 1,2,3 ORDER BY 1,2,3
    """,
    "vn_incentives": """
        SELECT program_code, import_mode::text, powertrain::text, incentive_scope, approval_required,
               condition_expression, benefit_expression
        FROM rules.automotive_incentive_program p JOIN ref.country c ON c.country_id=p.country_id
        WHERE c.iso2='VN' ORDER BY program_code
    """,
}

with engine.begin() as conn:
    for name, sql in queries.items():
        print("--", name)
        for row in conn.execute(text(sql)):
            print(tuple(row))
