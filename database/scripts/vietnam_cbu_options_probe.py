from pathlib import Path
from sqlalchemy import create_engine, text

root = Path(__file__).resolve().parents[2]
env = {}
for line in (root / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
engine = create_engine(
    f"postgresql+psycopg://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@{env.get('POSTGRES_HOST', '127.0.0.1')}:{env.get('POSTGRES_PORT','5432')}/{env['POSTGRES_DB']}"
)
with engine.begin() as conn:
    rows = conn.execute(text("""
        SELECT national_tariff_code, tariff_description
        FROM customs.vehicle_tariff_rate_line l
        JOIN ref.country c ON c.country_id=l.country_id
        JOIN rules.vehicle_tax_route r ON r.vehicle_tax_route_id=l.vehicle_tax_route_id
        WHERE c.iso2='VN' AND r.route_code='ROUTE-VN-01-CBU-NEW-PASSENGER'
          AND l.powertrain::text='BEV' AND l.origin_regime::text='MFN'
        ORDER BY national_tariff_code
    """)).fetchall()
    print(len(rows))
    for row in rows[:5]:
        print(row[0], row[1])
