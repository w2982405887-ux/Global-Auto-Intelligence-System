from pathlib import Path

api = Path("frontend/app/lib/api.ts")
s = api.read_text(encoding="utf-8")
s = s.replace(
    "  incentive: QuickEstimateScenario;\n  missing_items: string[];",
    "  incentive: QuickEstimateScenario;\n  policy_matches?: QuickPolicyMatch[];\n  missing_items: string[];",
)
s = s.replace(
    "export type QuickEstimateResult = {",
    '''export type QuickPolicyMatch = {
  program_code: string;
  program_name_cn: string;
  match_status: string;
  applies_to_paths: string[];
  incentive_scope: string;
  approval_required: boolean;
  effect_on_calculation: string;
  reason: string;
  included_in_current_numeric_result: boolean;
  verification_status: VerificationStatus;
};

export type QuickEstimateResult = {''',
)
s = s.replace(
    "  paths: QuickEstimatePath[];\n  assumptions:",
    "  paths: QuickEstimatePath[];\n  policy_matches?: QuickPolicyMatch[];\n  assumptions:",
)
api.write_text(s, encoding="utf-8")

page = Path("frontend/app/decision/new/page.tsx")
t = page.read_text(encoding="utf-8")
t = t.replace('const powertrains = ["ICE_GASOLINE", "HEV", "PHEV", "EREV", "BEV"] as const;', 'const powertrains = ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"] as const;')
t = t.replace('  const [form, setForm] = useState({\n    country_iso2: "MY",', '  const [form, setForm] = useState({\n    country_iso2: "VN",')
t = t.replace(
    '''      .then(() => Promise.all([
      getVehicleTariffOptions(
        form.country_iso2,
        "ROUTE-MY-01-CBU",
        form.powertrain,
        form.effective_date,
      ),
      getVehicleTariffOptions(
        form.country_iso2,
        "ROUTE-MY-02-CKD-WHOLE-KIT",
        form.powertrain,
        form.effective_date,
      ),
      ]))''',
    '''      .then(() => {
        const cbuRoute =
          form.country_iso2 === "VN"
            ? "ROUTE-VN-01-CBU-NEW-PASSENGER"
            : "ROUTE-MY-01-CBU";
        const ckdRoute =
          form.country_iso2 === "VN"
            ? "ROUTE-VN-CKD-PARTS-MAJOR-ESTIMATE"
            : "ROUTE-MY-02-CKD-WHOLE-KIT";
        return Promise.all([
          getVehicleTariffOptions(
            form.country_iso2,
            cbuRoute,
            form.powertrain,
            form.effective_date,
          ),
          form.country_iso2 === "VN"
            ? Promise.resolve({ total: 0, items: [] })
            : getVehicleTariffOptions(
                form.country_iso2,
                ckdRoute,
                form.powertrain,
                form.effective_date,
              ),
        ]);
      })''',
)
t = t.replace(
    '''  const needsCkd =
    (form.path === "AUTO" || form.path === "CKD") &&
    form.ckd_declaration_mode === "WHOLE_KIT";''',
    '''  const needsCkd =
    form.country_iso2 !== "VN" &&
    (form.path === "AUTO" || form.path === "CKD") &&
    form.ckd_declaration_mode === "WHOLE_KIT";''',
)
t = t.replace(
    '<h1>马来西亚汽车出口税负快速测算</h1>',
    '<h1>{form.country_iso2 === "VN" ? "越南汽车出口税负快速测算" : "马来西亚汽车出口税负快速测算"}</h1>',
)
t = t.replace(
    '''                <option value="MY">马来西亚 · MY</option>
              </select>''',
    '''                <option value="VN">越南 · VN</option>
                <option value="MY">马来西亚 · MY</option>
              </select>''',
)
t = t.replace(
    '''                    <option value="WHOLE_KIT">整套CKD单一税号</option>
                    <option value="PARTS_BOM">零部件BOM多税号</option>''',
    '''                    {form.country_iso2 !== "VN" && <option value="WHOLE_KIT">整套CKD单一税号</option>}
                    <option value="PARTS_BOM">零部件BOM多税号/主要大件估算</option>''',
)
t = t.replace(
    '''                {form.ckd_declaration_mode === "WHOLE_KIT" ? (''',
    '''                {form.country_iso2 === "VN" ? (
                  <div className="quick-bom-note">
                    越南CKD当前使用主要零件多税号估算，并自动匹配FTA与98.49等特殊政策；本地组装后SCT/VAT后续补充。
                  </div>
                ) : form.ckd_declaration_mode === "WHOLE_KIT" ? (''',
)
t = t.replace(
    '''            <section className="quick-assumptions">''',
    '''            {result.policy_matches && result.policy_matches.length > 0 && (
              <section className="quick-assumptions">
                <header>
                  <div>
                    <span>INCENTIVE MATCHING</span>
                    <h2>特殊政策匹配</h2>
                  </div>
                  <strong>已按路径、动力类型、原产国匹配</strong>
                </header>
                <div>
                  {result.policy_matches.map((policy) => (
                    <article key={policy.program_code}>
                      <CheckCircle2 size={17} />
                      <strong>{policy.program_name_cn}</strong>
                      <p>
                        {policy.match_status} · {policy.effect_on_calculation}
                      </p>
                    </article>
                  ))}
                </div>
              </section>
            )}

            <section className="quick-assumptions">''',
)
page.write_text(t, encoding="utf-8")
