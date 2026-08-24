from pathlib import Path

p = Path("database/scripts/vietnam_quick_estimate_smoke.py")
s = p.read_text(encoding="utf-8")
s = s.replace("from pathlib import Path\n", "from pathlib import Path\nimport sys\n")
s = s.replace(
    "from backend.app.services.quick_estimate import QuickEstimateService\n\nroot = Path(__file__).resolve().parents[2]",
    "root = Path(__file__).resolve().parents[2]\nsys.path.insert(0, str(root / \"backend\"))\nfrom app.services.quick_estimate import QuickEstimateService",
)
p.write_text(s, encoding="utf-8")
