from datetime import date
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "backend"))
from app.services.quick_estimate import QuickEstimateService
env = {}
for line in (root / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
url = f"postgresql+psycopg://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@127.0.0.1:{env.get('POSTGRES_PORT','5432')}/{env['POSTGRES_DB']}"
engine = create_engine(url)

with Session(engine) as session:
    result = QuickEstimateService(session).estimate(
        country_iso2="VN",
        origin_country_iso2="CN",
        effective_date=date(2026, 8, 4),
        path="AUTO",
        powertrain="BEV",
        cbu_tariff_code="8703809700",
        ckd_declaration_mode="PARTS_BOM",
        ckd_tariff_code=None,
        customs_value_cbu=Decimal("100"),
        customs_value_ckd=Decimal("100"),
    )
    print(result["country_iso2"], result["recommendation"]["confidence"])
    print("paths", [(p["path"], p["status"], p["incentive"]["regime"], p["incentive"]["effective_tax_rate"]) for p in result["paths"]])
    print("policies", len(result.get("policy_matches", [])))
