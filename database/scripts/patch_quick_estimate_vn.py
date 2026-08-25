from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
p = PROJECT_ROOT / "backend" / "app" / "services" / "quick_estimate.py"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "from sqlalchemy.orm import Session\n\n\n",
    "from sqlalchemy.orm import Session\n\nfrom app.services.vietnam_quick_estimate import VietnamQuickEstimateService\n\n\n",
)
old = '''        country_iso2 = country_iso2.upper()
        if country_iso2 != "MY":
            raise ValueError("快速测算第一版目前只支持马来西亚")'''
new = '''        country_iso2 = country_iso2.upper()
        if country_iso2 == "VN":
            return VietnamQuickEstimateService(self._session).estimate(
                origin_country_iso2=origin_country_iso2,
                effective_date=effective_date,
                path=path,
                powertrain=powertrain,
                cbu_tariff_code=cbu_tariff_code,
                ckd_declaration_mode=ckd_declaration_mode,
                customs_value_cbu=customs_value_cbu,
                customs_value_ckd=customs_value_ckd,
            )
        if country_iso2 != "MY":
            raise ValueError("快速测算目前支持马来西亚和越南")'''
if old not in s:
    raise SystemExit("anchor not found")
p.write_text(s.replace(old, new), encoding="utf-8")
