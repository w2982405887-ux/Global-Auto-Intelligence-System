from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
IN_CSV = PROJECT_ROOT / "database/reference_exports/vietnam_fta_major_parts_rates_extracted_round1.csv"
OUT_SQL = PROJECT_ROOT / "database/seeds/0025_vietnam_ckd_major_parts_tariff_round1.sql"
OUT_MATRIX = PROJECT_ROOT / "database/reference_exports/vietnam_ckd_powertrain_major_component_matrix_round1.csv"


COMPONENTS = [
    {
        "code": "VN-CKD-TRACTION-BATTERY",
        "name_cn": "动力电池",
        "name_en": "Traction battery",
        "system": "EV_POWERTRAIN",
        "hs6": ["850760"],
        "powertrains": ["HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.battery_chemistry", "part.pack_or_cell_module", "part.capacity_kwh", "origin.country_iso2"],
        "impact": "HIGH",
    },
    {
        "code": "VN-CKD-TRACTION-MOTOR",
        "name_cn": "电机",
        "name_en": "Traction motor",
        "system": "EV_POWERTRAIN",
        "hs6": ["850152", "850153"],
        "powertrains": ["HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.rated_output_kw", "part.ac_or_dc", "part.motor_only_or_drive_unit", "origin.country_iso2"],
        "impact": "HIGH",
    },
    {
        "code": "VN-CKD-E-POWER-CONTROL",
        "name_cn": "电控",
        "name_en": "Electric power control",
        "system": "EV_POWERTRAIN",
        "hs6": ["850440", "853710"],
        "powertrains": ["HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.inverter_converter_ecu", "part.operating_voltage_v", "origin.country_iso2"],
        "impact": "HIGH",
    },
    {
        "code": "VN-CKD-GASOLINE-ENGINE",
        "name_cn": "汽油发动机",
        "name_en": "Gasoline engine",
        "system": "ICE_POWERTRAIN",
        "hs6": ["840734"],
        "powertrains": ["ICE_GASOLINE", "HEV", "PHEV", "EREV"],
        "required_fields": ["engine.displacement_cc", "engine.spark_ignition", "engine.complete_engine", "origin.country_iso2"],
        "impact": "HIGH",
    },
    {
        "code": "VN-CKD-DIESEL-ENGINE",
        "name_cn": "柴油发动机",
        "name_en": "Diesel engine",
        "system": "ICE_POWERTRAIN",
        "hs6": ["840820"],
        "powertrains": ["ICE_DIESEL", "HEV", "PHEV", "EREV"],
        "required_fields": ["engine.displacement_cc", "engine.compression_ignition", "engine.complete_engine", "origin.country_iso2"],
        "impact": "HIGH",
    },
    {
        "code": "VN-CKD-TRANSMISSION-REDUCER",
        "name_cn": "变速箱/减速器",
        "name_en": "Transmission or reducer",
        "system": "DRIVELINE",
        "hs6": ["870840", "870899"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.transmission_or_reducer", "part.integrated_motor", "origin.country_iso2"],
        "impact": "HIGH",
    },
    {
        "code": "VN-CKD-BODY",
        "name_cn": "车身",
        "name_en": "Body or body parts",
        "system": "BODY",
        "hs6": ["870710", "870829"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.body_shell_or_panel", "vehicle.intended_heading", "origin.country_iso2"],
        "impact": "HIGH",
    },
    {
        "code": "VN-CKD-CHASSIS",
        "name_cn": "底盘",
        "name_en": "Chassis or frame",
        "system": "CHASSIS",
        "hs6": ["870899"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.frame_or_chassis_part", "part.with_engine_or_motor", "origin.country_iso2"],
        "impact": "HIGH",
    },
    {
        "code": "VN-CKD-SUSPENSION-AXLE",
        "name_cn": "悬架/车桥",
        "name_en": "Suspension or axle",
        "system": "CHASSIS",
        "hs6": ["870850", "870880", "732010"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.axle_suspension_or_spring", "vehicle.intended_heading", "origin.country_iso2"],
        "impact": "MEDIUM_HIGH",
    },
    {
        "code": "VN-CKD-STEERING",
        "name_cn": "转向",
        "name_en": "Steering",
        "system": "CHASSIS",
        "hs6": ["870894"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.steering_wheel_column_box_or_part", "origin.country_iso2"],
        "impact": "MEDIUM",
    },
    {
        "code": "VN-CKD-BRAKING",
        "name_cn": "制动",
        "name_en": "Braking",
        "system": "CHASSIS",
        "hs6": ["870830", "681381"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.brake_system_or_friction_material", "origin.country_iso2"],
        "impact": "MEDIUM",
    },
    {
        "code": "VN-CKD-TYRE-WHEEL",
        "name_cn": "轮胎/轮毂",
        "name_en": "Tyre or wheel",
        "system": "WHEEL_AND_TYRE",
        "hs6": ["401110", "870870"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.tyre_or_wheel", "part.size", "origin.country_iso2"],
        "impact": "MEDIUM",
    },
    {
        "code": "VN-CKD-THERMAL",
        "name_cn": "热管理",
        "name_en": "Thermal management",
        "system": "THERMAL_MANAGEMENT",
        "hs6": ["841520", "841330", "841381"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.hvac_pump_or_cooling_module", "part.engine_mounted", "origin.country_iso2"],
        "impact": "MEDIUM",
    },
    {
        "code": "VN-CKD-WIRING-HARNESS",
        "name_cn": "线束",
        "name_en": "Wiring harness",
        "system": "VEHICLE_ELECTRICAL",
        "hs6": ["854430"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.vehicle_wiring_set", "part.voltage_level", "origin.country_iso2"],
        "impact": "MEDIUM_HIGH",
    },
    {
        "code": "VN-CKD-SEATS",
        "name_cn": "座椅",
        "name_en": "Seats",
        "system": "INTERIOR",
        "hs6": ["940120"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.motor_vehicle_seat", "part.with_airbag_or_motor", "origin.country_iso2"],
        "impact": "MEDIUM",
    },
    {
        "code": "VN-CKD-GLASS",
        "name_cn": "玻璃",
        "name_en": "Glass",
        "system": "BODY",
        "hs6": ["700711", "700721"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.tempered_or_laminated", "part.vehicle_use", "origin.country_iso2"],
        "impact": "LOW_MEDIUM",
    },
    {
        "code": "VN-CKD-LIGHTING",
        "name_cn": "车灯",
        "name_en": "Vehicle lighting",
        "system": "VISIBILITY_LIGHTING",
        "hs6": ["851220"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.lighting_or_visual_signalling", "origin.country_iso2"],
        "impact": "LOW_MEDIUM",
    },
    {
        "code": "VN-CKD-INSTRUMENT-DISPLAY",
        "name_cn": "仪表/显示屏",
        "name_en": "Instrument or display",
        "system": "VEHICLE_ELECTRONICS",
        "hs6": ["902920", "853120"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.speedometer_display_or_panel", "origin.country_iso2"],
        "impact": "LOW_MEDIUM",
    },
    {
        "code": "VN-CKD-SAFETY",
        "name_cn": "安全气囊/安全带",
        "name_en": "Airbag or safety belt",
        "system": "SAFETY",
        "hs6": ["870895", "870821"],
        "powertrains": ["ICE_GASOLINE", "ICE_DIESEL", "HEV", "PHEV", "EREV", "BEV", "FCEV"],
        "required_fields": ["part.airbag_or_safety_belt", "origin.country_iso2"],
        "impact": "LOW_MEDIUM",
    },
]


def sql_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def json_sql(obj: object) -> str:
    return sql_quote(json.dumps(obj, ensure_ascii=False, separators=(",", ":"))) + "::jsonb"


def rate_decimal(rate: str) -> str | None:
    rate = rate.strip()
    if not rate or rate == "*":
        return None
    return f"{int(rate) / 100:.8f}"


def passenger_scope_description(description: str) -> bool:
    """Return whether a tariff line can be used for a new 87.03 vehicle.

    Shared component lines remain valid when they explicitly include 87.03.
    Lines restricted to tractors, buses, trucks, special-purpose vehicles,
    motorcycles or aircraft are excluded at seed-generation time so a future
    re-import cannot resurrect out-of-scope tax numbers.
    """
    text = (description or "").upper()
    if re.search(r"87[.]03(\D|$)", text):
        return True
    non_passenger = (
        r"87[.]01(\D|$)", r"87[.]02(\D|$)", r"87[.]04(\D|$)",
        r"87[.]05(\D|$)", r"87[.]11(\D|$)", r"88[.]",
        "TRACTOR", "MÁY KÉO", "MOTORCYCLE", "MOTOR CYCLE",
        "MÔ TÔ", "XE MÁY", "AIRCRAFT", "HELICOPTER",
    )
    return not any(re.search(marker, text) if marker.startswith("87[") or marker.startswith("88[") else marker in text for marker in non_passenger)


def write_matrix() -> None:
    OUT_MATRIX.parent.mkdir(parents=True, exist_ok=True)
    with OUT_MATRIX.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "powertrain",
                "component_code",
                "component_cn",
                "component_en",
                "hs6_candidates",
                "impact_weight",
                "required_fields",
                "note",
            ],
        )
        writer.writeheader()
        for c in COMPONENTS:
            for p in c["powertrains"]:
                writer.writerow(
                    {
                        "powertrain": p,
                        "component_code": c["code"],
                        "component_cn": c["name_cn"],
                        "component_en": c["name_en"],
                        "hs6_candidates": "|".join(c["hs6"]),
                        "impact_weight": c["impact"],
                        "required_fields": "|".join(c["required_fields"]),
                        "note": "FCEV excludes fuel-cell stack and hydrogen tanks until those component classes are added.",
                    }
                )


def generate_sql() -> tuple[int, Counter]:
    rows = list(csv.DictReader(IN_CSV.open(encoding="utf-8-sig")))
    selected = [
        r for r in rows
        if rate_decimal(r["rate_2026_percent"]) is not None
        and passenger_scope_description(r.get("description_vi", ""))
    ]
    c_by_hs = {hs: c for c in COMPONENTS for hs in c["hs6"]}
    counter = Counter((r["agreement"], r["origin_group"]) for r in selected)

    lines: list[str] = [
        "BEGIN;",
        "",
        "-- Vietnam CKD major-component tariff candidates, round 1.",
        "-- Scope: Vietnam, new passenger vehicle CKD, major components only.",
        "-- Rates are extracted from user-downloaded official preferential tariff appendices.",
        "",
        "INSERT INTO ref.trade_agreement (agreement_code, agreement_name, version, effective_from, record_status)",
        "VALUES",
        "  ('ACFTA','ASEAN-China Free Trade Area',1,DATE '2005-07-20','ACTIVE'),",
        "  ('RCEP','Regional Comprehensive Economic Partnership',1,DATE '2022-01-01','ACTIVE'),",
        "  ('ATIGA','ASEAN Trade in Goods Agreement',1,DATE '2010-05-17','ACTIVE')",
        "ON CONFLICT (agreement_code, version) DO NOTHING;",
        "",
        "WITH units (ccu_code, name_cn, name_en, vehicle_system, hs6_codes, powertrains, required_fields, impact_weight) AS (",
        "  VALUES",
    ]
    unit_values = []
    for c in COMPONENTS:
        unit_values.append(
            "    ("
            + ",".join(
                [
                    sql_quote(c["code"]),
                    sql_quote(c["name_cn"]),
                    sql_quote(c["name_en"]),
                    sql_quote(c["system"]),
                    json_sql(c["hs6"]),
                    json_sql(c["powertrains"]),
                    json_sql(c["required_fields"]),
                    sql_quote(c["impact"]),
                ]
            )
            + ")"
        )
    lines.append(",\n".join(unit_values))
    lines += [
        "), inserted AS (",
        "  INSERT INTO customs.customs_classification_unit (",
        "    ccu_code, ccu_name_cn, ccu_name_en, vehicle_system, unit_level,",
        "    function_description, technical_qualifiers, assembly_state, included_items,",
        "    excluded_items, required_input_fields, gri_2a_risk, version, record_status, verification_status",
        "  )",
        "  SELECT ccu_code, name_cn, name_en, vehicle_system,",
        "         'CUSTOMS_CLASSIFICATION_UNIT'::ref.ccu_unit_level,",
        "         'Vietnam CKD major-component generic classification unit. Final line depends on technical facts and origin regime.',",
        "         jsonb_build_object('country','VN','import_mode','CKD','powertrains',powertrains,'impact_weight',impact_weight),",
        "         'UNKNOWN'::ref.assembly_state,",
        "         jsonb_build_array(name_cn),",
        "         CASE WHEN ccu_code='VN-CKD-TRACTION-BATTERY' THEN jsonb_build_array('12V lead-acid starter battery unless selected separately') ELSE '[]'::jsonb END,",
        "         required_fields, 'MEDIUM'::ref.risk_level, 1, 'ACTIVE', 'CANDIDATE'",
        "  FROM units",
        "  ON CONFLICT (ccu_code, version) DO UPDATE SET",
        "    ccu_name_cn=EXCLUDED.ccu_name_cn,",
        "    ccu_name_en=EXCLUDED.ccu_name_en,",
        "    technical_qualifiers=EXCLUDED.technical_qualifiers,",
        "    required_input_fields=EXCLUDED.required_input_fields,",
        "    updated_at=now()",
        "  RETURNING ccu_id",
        ") SELECT count(*) FROM inserted;",
        "",
        "WITH units (ccu_code, hs6_codes) AS (",
        "  VALUES",
    ]
    lines.append(",\n".join(f"    ({sql_quote(c['code'])},{json_sql(c['hs6'])})" for c in COMPONENTS))
    lines += [
        "), expanded AS (",
        "  SELECT u.ccu_code, h.hs6_code, h.ordinality::integer AS candidate_rank",
        "  FROM units u",
        "  CROSS JOIN LATERAL jsonb_array_elements_text(u.hs6_codes) WITH ORDINALITY h(hs6_code, ordinality)",
        ")",
        "INSERT INTO customs.ccu_candidate_hs (",
        "  ccu_id, candidate_rank, hs_nomenclature_version, hs6_code, candidate_basis, exclusion_notes, verification_status",
        ")",
        "SELECT c.ccu_id, e.candidate_rank, 'AHTN-2022', e.hs6_code,",
        "       'Vietnam CKD major-component HS6 candidate. Select final VN line by component technical facts.',",
        "       'Do not use as final customs declaration without confirming national line, legal notes and GRI 2(a) risk.',",
        "       'CANDIDATE'",
        "FROM expanded e",
        "JOIN customs.customs_classification_unit c ON c.ccu_code=e.ccu_code AND c.version=1",
        "ON CONFLICT DO NOTHING;",
        "",
        "WITH rows (mapping_code, component_code, hs6_code, agreement, origin_group, national_tariff_code, vn_code, description_vi, rate_decimal, rates_extracted, source_file, rate_basis, excluded_origin_countries) AS (",
        "  VALUES",
    ]
    map_values = []
    seen = set()
    for r in selected:
        hs6 = r["hs6_code"]
        c = c_by_hs.get(hs6)
        if not c:
            continue
        nat = r["national_tariff_code"]
        # Keep mapping codes compact enough for readable SQL/debug.
        map_code = f"VN-CKD-PART-{r['agreement']}-{r['origin_group']}-{nat}-2026"
        key = (map_code, c["code"])
        if key in seen:
            continue
        seen.add(key)
        map_values.append(
            "    ("
            + ",".join(
                [
                    sql_quote(map_code),
                    sql_quote(c["code"]),
                    sql_quote(hs6),
                    sql_quote(r["agreement"]),
                    sql_quote(r["origin_group"]),
                    sql_quote(nat),
                    sql_quote(r["vn_code"]),
                    sql_quote(r["description_vi"]),
                    rate_decimal(r["rate_2026_percent"]) or "NULL",
                    sql_quote(r["rates_extracted"]),
                    sql_quote(r["source_file"]),
                    sql_quote(r["rate_selection_basis"]),
                    json_sql([item.strip() for item in r["country_markers"].replace("|", ",").split(",") if item.strip()]),
                ]
            )
            + ")"
        )
    lines.append(",\n".join(map_values))
    lines += [
        "), prepared AS (",
        "  SELECT rows.*,",
        "         country.country_id,",
        "         candidate.candidate_id,",
        "         agreement.trade_agreement_id,",
        "         clause.source_clause_id,",
        "         component.technical_qualifiers AS component_qualifiers",
        "  FROM rows",
        "  JOIN ref.country country ON country.iso2='VN'",
        "  JOIN customs.customs_classification_unit component ON component.ccu_code=rows.component_code AND component.version=1",
        "  JOIN customs.ccu_candidate_hs candidate ON candidate.ccu_id=component.ccu_id AND candidate.hs6_code=rows.hs6_code AND candidate.hs_nomenclature_version='AHTN-2022'",
        "  JOIN ref.trade_agreement agreement ON agreement.agreement_code=rows.agreement AND agreement.version=1",
        "  JOIN evidence.source_clause clause ON clause.clause_code = CASE rows.agreement",
        "      WHEN 'ACFTA' THEN 'VN-ACFTA-ORIGIN-PREFERENTIAL-DUTY'",
        "      WHEN 'ATIGA' THEN 'VN-ATIGA-ORIGIN-PREFERENTIAL-DUTY'",
        "      WHEN 'RCEP' THEN 'VN-RCEP-ORIGIN-PREFERENTIAL-DUTY'",
        "    END",
        ")",
        "INSERT INTO customs.tariff_mapping (",
        "  mapping_code, country_id, candidate_id, tariff_version, national_tariff_code,",
        "  tariff_description, origin_regime, trade_agreement_id, duty_rate, rate_type,",
        "  additional_measure, eligibility_condition, effective_from, effective_to,",
        "  version, source_clause_id, record_status, verification_status",
        ")",
        "SELECT mapping_code, country_id, candidate_id,",
        "       'VN-' || agreement || '-2026-CKD-MAJOR-PARTS',",
        "       national_tariff_code, description_vi, 'FTA'::ref.origin_regime,",
        "       trade_agreement_id, rate_decimal::numeric,",
        "       CASE WHEN rate_decimal::numeric = 0 THEN 'ZERO'::ref.rate_type ELSE 'AD_VALOREM'::ref.rate_type END,",
        "       jsonb_build_object(",
        "         'tax_type','IMPORT_DUTY',",
        "         'import_vat_standard_rate',0.10,",
        "         'vat_base_note','Vietnam import VAT usually follows customs value plus import duty and applicable import taxes; confirm at scenario level.',",
        "         'zero_rate_can_be_excluded_from_estimate', rate_decimal::numeric = 0,",
        "         'potential_9849_auto_parts_program_review_required', true",
        "       ),",
        "       jsonb_build_object(",
        "         'country','VN',",
        "         'scope','NEW_PASSENGER_CAR_CKD_MAJOR_COMPONENT_ESTIMATE',",
        "         'import_mode','CKD',",
        "         'agreement',agreement,",
        "         'origin_group',origin_group,",
        "         'requires_origin_rule',true,",
        "         'requires_direct_shipment',true,",
        "         'requires_proof_of_origin',true,",
        "         'national_code_display',vn_code,",
        "         'rates_extracted',rates_extracted,",
        "         'rate_basis',rate_basis,",
        "         'excluded_origin_countries',excluded_origin_countries,",
        "         'source_file',source_file,",
        "         'component_qualifiers',component_qualifiers",
        "       ),",
        "       DATE '2026-01-01', DATE '2027-01-01', 1, source_clause_id, 'ACTIVE', 'CANDIDATE'",
        "FROM prepared",
        "ON CONFLICT (mapping_code, version) DO UPDATE SET",
        "  duty_rate=EXCLUDED.duty_rate,",
        "  rate_type=EXCLUDED.rate_type,",
        "  additional_measure=EXCLUDED.additional_measure,",
        "  eligibility_condition=EXCLUDED.eligibility_condition,",
        "  source_clause_id=EXCLUDED.source_clause_id,",
        "  verification_status=EXCLUDED.verification_status,",
        "  updated_at=now();",
        "",
        "COMMIT;",
        "",
    ]
    OUT_SQL.write_text("\n".join(lines), encoding="utf-8")
    return len(map_values), counter


def main() -> int:
    write_matrix()
    count, counter = generate_sql()
    print(f"wrote {OUT_MATRIX}")
    print(f"wrote {OUT_SQL} tariff_mapping_rows={count}")
    for key, value in sorted(counter.items()):
        print(key, value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
