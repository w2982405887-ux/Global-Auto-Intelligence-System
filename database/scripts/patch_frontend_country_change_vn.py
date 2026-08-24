from pathlib import Path

p = Path("frontend/app/decision/new/page.tsx")
s = p.read_text(encoding="utf-8")
old = '''                onChange={(event) =>
                  setForm({ ...form, country_iso2: event.target.value })
                }'''
new = '''                onChange={(event) =>
                  setForm({
                    ...form,
                    country_iso2: event.target.value,
                    ckd_declaration_mode:
                      event.target.value === "VN" ? "PARTS_BOM" : "WHOLE_KIT",
                    cbu_tariff_code: "",
                    ckd_tariff_code: "",
                  })
                }'''
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
