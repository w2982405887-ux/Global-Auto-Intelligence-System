from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class IntelligenceRepository:
    """Read-only access layer for policy, route, tariff and CCU intelligence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _rows(result: Any) -> list[dict[str, Any]]:
        return [dict(row) for row in result.mappings()]

    @staticmethod
    def _policy_stage(*, effective_from: date, effective_to: date | None, as_of: date) -> str:
        """Classify a rule by its business time window, not only by record status."""
        if effective_from > as_of:
            return "FUTURE"
        if effective_to is not None and effective_to <= as_of:
            return "EXPIRED_RECENT"
        if effective_to is not None and (effective_to - as_of).days <= 180:
            return "EXPIRING"
        return "CURRENT"

    @staticmethod
    def _policy_classification(
        *,
        rule_code: str,
        rule_domain: str,
        import_mode: str | None = None,
    ) -> tuple[str, str, str]:
        """Return category, impact scope and impact level for the intelligence feed."""
        code = (rule_code or "").upper()
        domain = (rule_domain or "").upper()
        token = f"{domain} {code}"

        # FTA/origin policies must be classified before the generic DUTY
        # marker, otherwise ACFTA/RCEP records appear as ordinary tax rules.
        if domain == "FTA" or any(
            marker in token for marker in ("FTA", "ACFTA", "RCEP", "ATIGA", "ORIGIN", "RVC")
        ):
            category = "FTA_ORIGIN"
        elif domain in {
            "IMPORT_DUTY",
            "SALES_TAX",
            "EXCISE",
            "VAT_GST",
            "VALUATION",
            "REGISTRATION_FEE",
        } or any(marker in token for marker in ("DUTY", "TAX", "SST", "VAT", "EXCISE")):
            category = "TAX"
        elif domain in {"APPROVAL", "QUOTA"} or any(marker in token for marker in ("AP-", "APPROVAL", "PERMIT", "QUOTA", "MRA")):
            category = "ACCESS_APPROVAL"
        elif domain in {"INCENTIVE", "LOCALIZATION"} or any(marker in token for marker in ("INCENTIVE", "LOCAL", "TKDN", "98.49")):
            category = "INCENTIVE_LOCALIZATION"
        elif domain == "CUSTOMS_CLASSIFICATION" or any(marker in token for marker in ("HS", "CLASSIFICATION", "GRI")):
            category = "CLASSIFICATION"
        else:
            category = "STRATEGY"

        normalized_import_mode = (import_mode or "").upper()
        if (
            "CBU" in code
            and "CKD" not in code
        ) or normalized_import_mode == "CBU":
            scope = "CBU"
        elif (
            "CKD" in code
            or "LOCAL" in code
            or "98.49" in code
            or "9849" in code
            or normalized_import_mode in {"PARTS", "LOCAL_PRODUCTION", "CKD"}
        ):
            scope = "CKD"
        elif any(marker in code for marker in ("FTA", "RCEP", "ACFTA", "ATIGA")):
            scope = "BOTH"
        else:
            scope = "BOTH"

        if category in {"TAX", "FTA_ORIGIN", "ACCESS_APPROVAL"} or any(
            marker in code for marker in ("CBU", "CKD", "ACFTA", "RCEP", "ATIGA", "AP-")
        ):
            impact = "HIGH"
        elif category in {"INCENTIVE_LOCALIZATION", "CLASSIFICATION"}:
            impact = "MEDIUM"
        else:
            impact = "LOW"
        return category, scope, impact

    @staticmethod
    def _policy_freshness(*, last_verified_at: datetime | None, as_of: date) -> str:
        if last_verified_at is None:
            return "UNVERIFIED"
        verified_date = last_verified_at.date()
        return "RECENT" if (as_of - verified_date).days <= 180 else "STALE"

    def dashboard_overview(self, *, as_of: date) -> dict[str, Any]:
        counts = dict(
            self._session.execute(
                text(
                    """
                    SELECT
                      (
                        SELECT count(DISTINCT country.country_id)
                        FROM ref.country country
                        WHERE country.record_status = 'ACTIVE'
                          AND (
                            EXISTS (
                              SELECT 1
                              FROM rules.country_rule_card rule
                              WHERE rule.country_id = country.country_id
                                AND rule.record_status = 'ACTIVE'
                            )
                            OR EXISTS (
                              SELECT 1
                              FROM rules.vehicle_tax_route route
                              WHERE route.country_id = country.country_id
                                AND route.record_status = 'ACTIVE'
                            )
                          )
                      ) AS connected_country_count,
                      (
                        SELECT count(*)
                        FROM rules.country_rule_card
                        WHERE record_status = 'ACTIVE'
                      ) AS rule_count,
                      (
                        SELECT count(*)
                        FROM rules.automotive_incentive_program program
                        JOIN ref.country country
                          ON country.country_id = program.country_id
                        WHERE program.record_status = 'ACTIVE'
                          AND country.iso2 IN ('MY', 'VN')
                          AND (
                            program.effective_from > :as_of
                            OR (
                              program.effective_from <= :as_of
                              AND (program.effective_to IS NULL OR program.effective_to > :as_of)
                            )
                          )
                      ) AS special_policy_count,
                      (
                        SELECT count(*)
                        FROM rules.automotive_incentive_program program
                        JOIN ref.country country
                          ON country.country_id = program.country_id
                        WHERE program.record_status = 'ACTIVE'
                          AND country.iso2 IN ('MY', 'VN')
                          AND program.effective_from <= :as_of
                          AND (program.effective_to IS NULL OR program.effective_to > :as_of)
                      ) AS active_special_policy_count,
                      (
                        SELECT count(*)
                        FROM rules.automotive_incentive_program program
                        JOIN ref.country country
                          ON country.country_id = program.country_id
                        WHERE program.record_status = 'ACTIVE'
                          AND country.iso2 IN ('MY', 'VN')
                          AND program.verification_status::text IN ('CANDIDATE', 'UNVERIFIED')
                          AND (
                            program.effective_from > :as_of
                            OR (
                              program.effective_from <= :as_of
                              AND (program.effective_to IS NULL OR program.effective_to > :as_of)
                            )
                          )
                      ) AS pending_review_policy_count,
                      (
                        SELECT count(*)
                        FROM evidence.source_document
                        WHERE record_status = 'ACTIVE'
                      ) AS source_count,
                      (
                        SELECT count(*)
                        FROM customs.customs_classification_unit
                        WHERE record_status = 'ACTIVE'
                          AND unit_level::text = 'CUSTOMS_CLASSIFICATION_UNIT'
                      ) AS ccu_count,
                      (
                        SELECT count(*)
                        FROM customs.tariff_mapping
                        WHERE record_status = 'ACTIVE'
                      ) AS ccu_tariff_mapping_count,
                      (
                        SELECT count(*)
                        FROM customs.vehicle_tariff_rate_line
                        WHERE record_status = 'ACTIVE'
                      ) AS vehicle_tariff_line_count,
                      (
                        SELECT count(*)
                        FROM audit.missing_data
                        WHERE status = 'OPEN'
                      ) AS open_missing_data,
                      (
                        SELECT count(*)
                        FROM (
                          SELECT effective_from
                          FROM rules.country_rule_card
                          WHERE record_status = 'ACTIVE'
                            AND effective_from > :as_of
                          UNION ALL
                          SELECT effective_from
                          FROM rules.approval_matrix
                          WHERE record_status = 'ACTIVE'
                            AND effective_from > :as_of
                          UNION ALL
                          SELECT effective_from
                          FROM customs.vehicle_tariff_rate_line
                          WHERE record_status = 'ACTIVE'
                            AND effective_from > :as_of
                          UNION ALL
                          SELECT effective_from
                          FROM rules.automotive_incentive_program program
                          JOIN ref.country country
                            ON country.country_id = program.country_id
                          WHERE program.record_status = 'ACTIVE'
                            AND country.iso2 IN ('MY', 'VN')
                            AND effective_from > :as_of
                        ) future_nodes
                      ) AS future_effective_count,
                      (
                        SELECT max(last_changed)
                        FROM (
                          SELECT max(updated_at) AS last_changed
                          FROM rules.country_rule_card
                          UNION ALL
                          SELECT max(updated_at)
                          FROM rules.vehicle_tax_route
                          UNION ALL
                          SELECT max(updated_at)
                          FROM customs.tariff_mapping
                          UNION ALL
                          SELECT max(updated_at)
                          FROM rules.automotive_incentive_program
                        ) timestamps
                      ) AS last_updated_at
                    """
                ),
                {"as_of": as_of},
            ).mappings().one()
        )
        # The homepage feed is intentionally an incentive/policy feed rather
        # than a copy of the country rule-card registry.  Country rule cards
        # are useful for internal readiness, but they are not the complete
        # set of special benefits that the export team needs to review every
        # day.  The two currently connected markets have their special
        # programs in automotive_incentive_program, so read that table here.
        recent_policies = self._rows(
            self._session.execute(
                text(
                    """
                    SELECT
                      program.program_code AS rule_code,
                      country.iso2,
                      country.country_name_cn,
                      program.program_name_cn AS rule_name_cn,
                      program.incentive_scope AS rule_domain,
                      program.condition_expression,
                      program.benefit_expression,
                      program.approval_required,
                      program.import_mode::text AS import_mode,
                      program.powertrain::text AS powertrain,
                      program.incentive_scope,
                      program.condition_expression AS rule_content,
                      program.verification_status::text AS verification_status,
                      program.effective_from,
                      program.effective_to,
                      source.source_code,
                      source.document_title,
                      source.source_type,
                      source.document_number,
                      clause.locator_value AS source_locator,
                      clause.locator_type,
                      source.canonical_url,
                      auth.authority_name,
                      program.updated_at,
                      program.updated_at AS last_verified_at
                    FROM rules.automotive_incentive_program program
                    JOIN ref.country country
                      ON country.country_id = program.country_id
                    LEFT JOIN evidence.source_clause clause
                      ON clause.source_clause_id = program.source_clause_id
                    LEFT JOIN evidence.source_document source
                      ON source.source_document_id = clause.source_document_id
                    LEFT JOIN ref.authority auth
                      ON auth.authority_id = source.authority_id
                    WHERE program.record_status = 'ACTIVE'
                      AND country.iso2 IN ('MY', 'VN')
                      AND (
                        program.effective_from > :as_of
                        OR (
                          program.effective_from <= :as_of
                          AND (program.effective_to IS NULL OR program.effective_to > :as_of)
                        )
                      )
                    ORDER BY
                      CASE
                        WHEN program.effective_from > :as_of THEN 0
                        WHEN program.effective_to IS NOT NULL
                          AND program.effective_to <= (:as_of + INTERVAL '180 days') THEN 1
                        ELSE 2
                      END,
                      program.effective_from DESC,
                      program.updated_at DESC,
                      program.program_code
                    LIMIT 12
                    """
                ),
                {"as_of": as_of},
            )
        )
        for policy in recent_policies:
            policy["source_reference"] = {
                "source_id": policy.get("source_code") or "",
                "document_title": policy.get("document_title") or "",
                "document_number": policy.get("document_number"),
                "source_type": policy.get("source_type") or "",
                "authority_name": policy.get("authority_name") or "",
                "official_url": policy.get("canonical_url"),
                "locator": {
                    "locator_type": policy.get("locator_type") or "",
                    "locator_value": policy.get("source_locator") or "",
                },
            }
            # Preserve structured conditions/benefits for the review drawer.
            # Existing country-rule consumers can ignore these optional fields.
            policy["rule_content"] = (
                policy.get("incentive_scope")
                or "该政策的结构化条件和效果见政策详情。"
            )
            policy["policy_stage"] = self._policy_stage(
                effective_from=policy["effective_from"],
                effective_to=policy["effective_to"],
                as_of=as_of,
            )
            category, scope, impact = self._policy_classification(
                rule_code=policy["rule_code"],
                rule_domain=policy["rule_domain"],
                import_mode=policy.get("import_mode"),
            )
            policy["policy_category"] = category
            policy["impact_scope"] = scope
            policy["business_impact"] = impact
            policy["freshness_status"] = self._policy_freshness(
                last_verified_at=policy.get("last_verified_at"),
                as_of=as_of,
            )
        return {**counts, "as_of": as_of, "recent_policies": recent_policies}

    def country(self, *, iso2: str) -> dict[str, Any] | None:
        row = self._session.execute(
            text(
                """
                SELECT
                  iso2,
                  iso3,
                  country_name_cn AS name_cn,
                  country_name_en AS name_en,
                  currency_code,
                  timezone_name
                FROM ref.country
                WHERE iso2 = :iso2
                  AND record_status = 'ACTIVE'
                """
            ),
            {"iso2": iso2.upper()},
        ).mappings().one_or_none()
        return dict(row) if row else None

    def tax_routes(self, *, iso2: str, as_of: date) -> list[dict[str, Any]]:
        return self._rows(
            self._session.execute(
                text(
                    """
                    SELECT
                      route.decision_order,
                      route.route_code,
                      route.route_name_cn,
                      route.route_name_en,
                      route.route_kind,
                      route.import_mode::text AS import_mode,
                      route.classification_granularity,
                      route.decision_condition,
                      route.required_input_fields,
                      route.fallback_route_code,
                      route.decision_note,
                      route.effective_from,
                      route.effective_to,
                      route.verification_status::text AS verification_status
                    FROM rules.vehicle_tax_route route
                    JOIN ref.country country
                      ON country.country_id = route.country_id
                    WHERE country.iso2 = :iso2
                      AND route.record_status = 'ACTIVE'
                      AND route.effective_from <= :as_of
                      AND (route.effective_to IS NULL OR route.effective_to > :as_of)
                    ORDER BY route.decision_order
                    """
                ),
                {"iso2": iso2.upper(), "as_of": as_of},
            )
        )

    def route_readiness(self, *, iso2: str, as_of: date) -> list[dict[str, Any]]:
        rows = self._rows(
            self._session.execute(
                text(
                    """
                    WITH country_ccu AS (
                      SELECT
                        count(DISTINCT ccu.ccu_id) FILTER (
                          WHERE ccu.record_status = 'ACTIVE'
                        ) AS active_ccu_count,
                        count(DISTINCT ccu.ccu_id) FILTER (
                          WHERE mapping.mapping_id IS NOT NULL
                        ) AS mapped_ccu_count,
                        count(DISTINCT mapping.mapping_id) AS ccu_tariff_mapping_count,
                        count(DISTINCT mapping.mapping_id) FILTER (
                          WHERE mapping.duty_rate IS NULL
                        ) AS ccu_mapping_missing_duty_count
                      FROM ref.country country
                      CROSS JOIN customs.customs_classification_unit ccu
                      LEFT JOIN customs.ccu_candidate_hs candidate
                        ON candidate.ccu_id = ccu.ccu_id
                      LEFT JOIN customs.tariff_mapping mapping
                        ON mapping.candidate_id = candidate.candidate_id
                       AND mapping.country_id = country.country_id
                       AND mapping.record_status = 'ACTIVE'
                       AND mapping.effective_from <= :as_of
                       AND (mapping.effective_to IS NULL OR mapping.effective_to > :as_of)
                      WHERE country.iso2 = :iso2
                        AND ccu.unit_level::text = 'CUSTOMS_CLASSIFICATION_UNIT'
                    ),
                    bucket_count AS (
                      SELECT count(*) AS kd_tax_bucket_count
                      FROM rules.kd_tax_bucket_definition bucket
                      JOIN ref.country country
                        ON country.country_id = bucket.country_id
                      WHERE country.iso2 = :iso2
                        AND bucket.record_status = 'ACTIVE'
                        AND bucket.effective_from <= :as_of
                        AND (bucket.effective_to IS NULL OR bucket.effective_to > :as_of)
                    )
                    SELECT
                      route.decision_order,
                      route.route_code,
                      route.route_name_cn,
                      route.verification_status::text AS route_verification_status,
                      count(line.vehicle_tariff_rate_line_id) AS tariff_line_count,
                      count(*) FILTER (WHERE line.origin_regime::text = 'MFN')
                        AS mfn_line_count,
                      count(*) FILTER (WHERE agreement.agreement_code = 'ACFTA')
                        AS acfta_line_count,
                      count(*) FILTER (WHERE agreement.agreement_code = 'RCEP')
                        AS rcep_line_count,
                      count(*) FILTER (
                        WHERE line.vehicle_tariff_rate_line_id IS NOT NULL
                          AND line.import_duty_rate IS NULL
                      ) AS missing_public_duty_rate_count,
                      count(*) FILTER (
                        WHERE line.verification_status::text IN ('VERIFIED', 'RULING_CONFIRMED')
                      ) AS verified_tariff_line_count,
                      CASE
                        WHEN route.route_kind IN ('PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD')
                        THEN bucket_count.kd_tax_bucket_count
                        ELSE 0
                      END AS kd_tax_bucket_count,
                      CASE
                        WHEN route.route_kind IN ('PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD')
                        THEN country_ccu.active_ccu_count
                        ELSE 0
                      END AS active_ccu_count,
                      CASE
                        WHEN route.route_kind IN ('PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD')
                        THEN country_ccu.mapped_ccu_count
                        ELSE 0
                      END AS mapped_ccu_count,
                      CASE
                        WHEN route.route_kind IN ('PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD')
                        THEN country_ccu.ccu_tariff_mapping_count
                        ELSE 0
                      END AS ccu_tariff_mapping_count,
                      CASE
                        WHEN route.route_kind IN ('PARTS_SUBASSEMBLIES', 'PART_LEVEL', 'MIXED_KD')
                        THEN country_ccu.ccu_mapping_missing_duty_count
                        ELSE 0
                      END AS ccu_mapping_missing_duty_count
                    FROM rules.vehicle_tax_route route
                    JOIN ref.country country
                      ON country.country_id = route.country_id
                    LEFT JOIN customs.vehicle_tariff_rate_line line
                      ON line.vehicle_tax_route_id = route.vehicle_tax_route_id
                     AND line.record_status = 'ACTIVE'
                     AND line.effective_from <= :as_of
                     AND (line.effective_to IS NULL OR line.effective_to > :as_of)
                    LEFT JOIN ref.trade_agreement agreement
                      ON agreement.trade_agreement_id = line.trade_agreement_id
                    CROSS JOIN country_ccu
                    CROSS JOIN bucket_count
                    WHERE country.iso2 = :iso2
                      AND route.record_status = 'ACTIVE'
                      AND route.effective_from <= :as_of
                      AND (route.effective_to IS NULL OR route.effective_to > :as_of)
                    GROUP BY
                      route.decision_order,
                      route.route_code,
                      route.route_name_cn,
                      route.route_kind,
                      route.verification_status,
                      bucket_count.kd_tax_bucket_count,
                      country_ccu.active_ccu_count,
                      country_ccu.mapped_ccu_count,
                      country_ccu.ccu_tariff_mapping_count,
                      country_ccu.ccu_mapping_missing_duty_count
                    ORDER BY route.decision_order
                    """
                ),
                {"iso2": iso2.upper(), "as_of": as_of},
            )
        )
        for row in rows:
            total = int(row["tariff_line_count"])
            active_ccu = int(row["active_ccu_count"])
            if total:
                row["completeness_percent"] = round(
                    int(row["verified_tariff_line_count"]) * 100 / total
                )
            elif active_ccu:
                row["completeness_percent"] = round(
                    int(row["mapped_ccu_count"]) * 100 / active_ccu
                )
            else:
                row["completeness_percent"] = 0
        return rows

    def policy_nodes(self, *, iso2: str, as_of: date) -> dict[str, Any]:
        row = self._session.execute(
            text(
                """
                SELECT
                  count(*) FILTER (
                    WHERE effective_from <= :as_of
                      AND (effective_to IS NULL OR effective_to > :as_of)
                  ) AS current,
                  count(*) FILTER (WHERE effective_from > :as_of) AS future_effective,
                  count(*) FILTER (
                    WHERE effective_to > :as_of
                      AND effective_to <= (:as_of + interval '180 days')::date
                  ) AS expiring
                FROM (
                  SELECT rule.effective_from, rule.effective_to
                  FROM rules.country_rule_card rule
                  JOIN ref.country country ON country.country_id = rule.country_id
                  WHERE country.iso2 = :iso2
                    AND rule.record_status = 'ACTIVE'
                  UNION ALL
                  SELECT approval.effective_from, approval.effective_to
                  FROM rules.approval_matrix approval
                  JOIN ref.country country ON country.country_id = approval.country_id
                  WHERE country.iso2 = :iso2
                    AND approval.record_status = 'ACTIVE'
                  UNION ALL
                  SELECT line.effective_from, line.effective_to
                  FROM customs.vehicle_tariff_rate_line line
                  JOIN ref.country country ON country.country_id = line.country_id
                  WHERE country.iso2 = :iso2
                    AND line.record_status = 'ACTIVE'
                ) nodes
                """
            ),
            {"iso2": iso2.upper(), "as_of": as_of},
        ).mappings().one()
        statistics = {key: int(value) for key, value in row.items()}

        # Highlighted policies: future + expiring + recently-updated, with sources
        highlights = self._rows(
            self._session.execute(
                text(
                    """
                    SELECT
                      rule.rule_code,
                      rule.rule_name_cn,
                      rule.rule_domain::text AS rule_domain,
                      rule.verification_status::text AS verification_status,
                      rule.effective_from,
                      rule.effective_to,
                      rule.updated_at,
                      source.source_code AS source_id,
                      source.document_title,
                      source.document_number,
                      source.source_type,
                      source.canonical_url AS official_url,
                      source_auth.authority_name,
                      clause.locator_type,
                      clause.locator_value AS source_locator
                    FROM rules.country_rule_card rule
                    JOIN ref.country country
                      ON country.country_id = rule.country_id
                    JOIN evidence.source_clause clause
                      ON clause.source_clause_id = rule.source_clause_id
                    JOIN evidence.source_document source
                      ON source.source_document_id = clause.source_document_id
                    LEFT JOIN ref.authority source_auth
                      ON source_auth.authority_id = source.authority_id
                    WHERE country.iso2 = :iso2
                      AND rule.record_status = 'ACTIVE'
                      AND (
                        rule.effective_from > :as_of
                        OR (
                          rule.effective_to > :as_of
                          AND rule.effective_to <= (:as_of + interval '180 days')::date
                        )
                        OR rule.effective_from <= :as_of
                          AND (rule.effective_to IS NULL OR rule.effective_to > :as_of)
                      )
                    ORDER BY
                      CASE
                        WHEN rule.effective_from > :as_of THEN 0
                        WHEN rule.effective_to IS NOT NULL
                          AND rule.effective_to <= (:as_of + interval '180 days')::date THEN 1
                        ELSE 2
                      END,
                      COALESCE(rule.verified_at, rule.updated_at) DESC,
                      rule.rule_code
                    LIMIT 10
                    """
                ),
                {"iso2": iso2.upper(), "as_of": as_of},
            )
        )

        return {
            "statistics": statistics,
            "highlights": highlights,
        }

    def open_missing_data_count(self) -> int:
        return int(
            self._session.execute(
                text("SELECT count(*) FROM audit.missing_data WHERE status = 'OPEN'")
            ).scalar_one()
        )

    def last_verified_at(self, *, iso2: str) -> Any:
        return self._session.execute(
            text(
                """
                SELECT max(changed_at)
                FROM (
                  SELECT max(rule.verified_at) AS changed_at
                  FROM rules.country_rule_card rule
                  JOIN ref.country country ON country.country_id = rule.country_id
                  WHERE country.iso2 = :iso2
                  UNION ALL
                  SELECT max(route.updated_at)
                  FROM rules.vehicle_tax_route route
                  JOIN ref.country country ON country.country_id = route.country_id
                  WHERE country.iso2 = :iso2
                  UNION ALL
                  SELECT max(mapping.updated_at)
                  FROM customs.tariff_mapping mapping
                  JOIN ref.country country ON country.country_id = mapping.country_id
                  WHERE country.iso2 = :iso2
                ) timestamps
                """
            ),
            {"iso2": iso2.upper()},
        ).scalar_one()

    def rules(
        self,
        *,
        iso2: str,
        as_of: date,
        domain: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        filters = [
            "country.iso2 = :iso2",
            "rule.record_status = 'ACTIVE'",
            "rule.effective_from <= :as_of",
            "(rule.effective_to IS NULL OR rule.effective_to > :as_of)",
        ]
        params: dict[str, Any] = {"iso2": iso2.upper(), "as_of": as_of}

        if domain:
            filters.append("rule.rule_domain::text = :domain")
            params["domain"] = domain
        if status:
            filters.append("rule.verification_status::text = :status")
            params["status"] = status
        if keyword:
            filters.append(
                "(rule.rule_name_cn ILIKE :kw"
                " OR rule.rule_code ILIKE :kw"
                " OR rule.rule_domain::text ILIKE :kw"
                " OR rule.rule_content ILIKE :kw"
                " OR source.document_title ILIKE :kw"
                " OR authority.authority_name ILIKE :kw)"
            )
            params["kw"] = f"%{keyword}%"

        where_clause = " AND ".join(filters)

        count_sql = f"""
            SELECT count(*) AS total
            FROM rules.country_rule_card rule
            JOIN ref.country country ON country.country_id = rule.country_id
            LEFT JOIN ref.authority authority ON authority.authority_id = rule.authority_id
            JOIN evidence.source_clause clause ON clause.source_clause_id = rule.source_clause_id
            JOIN evidence.source_document source ON source.source_document_id = clause.source_document_id
            WHERE {where_clause}
        """
        total = int(self._session.execute(text(count_sql), params).scalar_one())

        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        rows = self._rows(
            self._session.execute(
                text(
                    f"""
                    SELECT
                      rule.rule_code,
                      rule.rule_domain::text AS rule_domain,
                      rule.rule_name_cn,
                      rule.rule_content,
                      rule.condition_expression,
                      rule.formula_expression,
                      rule.tariff_version,
                      rule.effective_from,
                      rule.effective_to,
                      rule.version,
                      rule.record_status::text AS record_status,
                      rule.verification_status::text AS verification_status,
                      rule.verified_at,
                      rule.verified_by,
                      authority.authority_name,
                      source.source_code,
                      source.source_type,
                      source.document_title,
                      source.document_number,
                      source.canonical_url,
                      source.content_sha256,
                      clause.clause_code,
                      clause.source_clause_id AS clause_id,
                      clause.locator_type,
                      clause.locator_value,
                      clause.evidence_summary
                    FROM rules.country_rule_card rule
                    JOIN ref.country country
                      ON country.country_id = rule.country_id
                    LEFT JOIN ref.authority authority
                      ON authority.authority_id = rule.authority_id
                    JOIN evidence.source_clause clause
                      ON clause.source_clause_id = rule.source_clause_id
                    JOIN evidence.source_document source
                      ON source.source_document_id = clause.source_document_id
                    WHERE {where_clause}
                    ORDER BY rule.rule_domain, rule.rule_code
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
        )

        # Inject summaries
        from app.services.policy_summarizer import summarize_policy
        items: list[dict[str, Any]] = []
        for row in rows:
            summaries = summarize_policy(row)
            item = dict(row)
            item["condition_summary"] = summaries.condition_summary
            item["condition_summary_status"] = summaries.condition_summary_status
            item["formula_summary"] = summaries.formula_summary
            item["formula_summary_status"] = summaries.formula_summary_status
            item["impact_scope"] = summaries.impact_scope
            # Build evidence (1-N support — MVP has one clause per rule)
            item["evidence"] = [{
                "document_id": str(item.get("source_code", "")),
                "clause_id": str(item.get("clause_id", "")),
                "document_title": item.get("document_title", ""),
                "authority_name": item.get("authority_name", ""),
                "document_number": item.get("document_number"),
                "source_type": item.get("source_type", ""),
                "evidence_role": summaries.evidence_roles.get(
                    str(item.get("clause_code", "")), "TARIFF_RATE",
                ),
                "official_url": item.get("canonical_url"),
                "locator_type": item.get("locator_type", ""),
                "locator_value": item.get("locator_value", ""),
                "evidence_summary": item.get("evidence_summary", ""),
            }]
            items.append(item)

        return {"total": total, "page": page, "page_size": page_size, "items": items}

    def vehicle_tariffs(
        self,
        *,
        iso2: str,
        as_of: date,
        route_code: str | None,
        origin_regime: str | None,
        agreement_code: str | None,
        hs6_code: str | None,
        powertrain: str | None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        filters = [
            "country.iso2 = :iso2",
            "line.record_status = 'ACTIVE'",
            "line.effective_from <= :as_of",
            "(line.effective_to IS NULL OR line.effective_to > :as_of)",
        ]
        params: dict[str, Any] = {
            "iso2": iso2.upper(),
            "as_of": as_of,
            "limit": limit,
            "offset": offset,
        }
        optional = {
            "route_code": ("route.route_code = :route_code", route_code),
            "origin_regime": ("line.origin_regime::text = :origin_regime", origin_regime),
            "agreement_code": ("agreement.agreement_code = :agreement_code", agreement_code),
            "hs6_code": ("line.hs6_code = :hs6_code", hs6_code),
            "powertrain": ("line.powertrain::text = :powertrain", powertrain),
        }
        for name, (expression, value) in optional.items():
            if value:
                filters.append(expression)
                params[name] = value
        where_clause = " AND ".join(filters)
        total = int(
            self._session.execute(
                text(
                    f"""
                    SELECT count(*)
                    FROM customs.vehicle_tariff_rate_line line
                    JOIN rules.vehicle_tax_route route
                      ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
                    JOIN ref.country country ON country.country_id = line.country_id
                    LEFT JOIN ref.trade_agreement agreement
                      ON agreement.trade_agreement_id = line.trade_agreement_id
                    WHERE {where_clause}
                    """
                ),
                params,
            ).scalar_one()
        )
        items = self._rows(
            self._session.execute(
                text(
                    f"""
                    SELECT
                      line.vehicle_tariff_rate_line_id,
                      route.route_code,
                      route.route_kind,
                      line.tariff_schedule_code,
                      line.tariff_year,
                      line.origin_regime::text AS origin_regime,
                      agreement.agreement_code,
                      line.hs6_code,
                      line.national_tariff_code,
                      line.linked_pdk_tariff_code,
                      line.tariff_description,
                      line.powertrain::text AS powertrain,
                      line.import_duty_rate,
                      line.sales_tax_rate,
                      line.excise_duty_rate,
                      line.sales_tax_treatment,
                      line.excise_treatment,
                      line.eligibility_condition,
                      line.verification_status::text AS verification_status,
                      source.source_code,
                      clause.locator_value AS source_locator,
                      source.canonical_url,
                      line.effective_from,
                      line.effective_to
                    FROM customs.vehicle_tariff_rate_line line
                    JOIN rules.vehicle_tax_route route
                      ON route.vehicle_tax_route_id = line.vehicle_tax_route_id
                    JOIN ref.country country ON country.country_id = line.country_id
                    LEFT JOIN ref.trade_agreement agreement
                      ON agreement.trade_agreement_id = line.trade_agreement_id
                    JOIN evidence.source_clause clause
                      ON clause.source_clause_id = line.tariff_source_clause_id
                    JOIN evidence.source_document source
                      ON source.source_document_id = clause.source_document_id
                    WHERE {where_clause}
                    ORDER BY
                      route.decision_order,
                      line.national_tariff_code,
                      line.origin_regime,
                      agreement.agreement_code NULLS FIRST
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
        )
        return total, items

    def ccus(
        self, *, country_iso2: str, query: str | None, limit: int, offset: int
    ) -> tuple[int, list[dict[str, Any]]]:
        filters = [
            "ccu.record_status = 'ACTIVE'",
            "ccu.unit_level::text = 'CUSTOMS_CLASSIFICATION_UNIT'",
        ]
        params: dict[str, Any] = {
            "country_iso2": country_iso2.upper(),
            "limit": limit,
            "offset": offset,
        }
        if query:
            filters.append(
                """
                (
                  ccu.ccu_code ILIKE :query
                  OR ccu.ccu_name_cn ILIKE :query
                  OR ccu.ccu_name_en ILIKE :query
                  OR ccu.vehicle_system ILIKE :query
                )
                """
            )
            params["query"] = f"%{query}%"
        where_clause = " AND ".join(filters)
        total = int(
            self._session.execute(
                text(
                    f"""
                    SELECT count(*)
                    FROM customs.customs_classification_unit ccu
                    WHERE {where_clause}
                    """
                ),
                params,
            ).scalar_one()
        )
        items = self._rows(
            self._session.execute(
                text(
                    f"""
                    SELECT
                      ccu.ccu_code,
                      ccu.ccu_name_cn,
                      ccu.ccu_name_en,
                      ccu.vehicle_system,
                      ccu.unit_level::text AS unit_level,
                      ccu.function_description,
                      ccu.assembly_state::text AS assembly_state,
                      ccu.required_input_fields,
                      ccu.gri_2a_risk::text AS gri_2a_risk,
                      ccu.verification_status::text AS verification_status,
                      count(DISTINCT candidate.candidate_id) AS hs6_candidate_count,
                      count(DISTINCT mapping.mapping_id) AS tariff_option_count
                    FROM customs.customs_classification_unit ccu
                    LEFT JOIN customs.ccu_candidate_hs candidate
                      ON candidate.ccu_id = ccu.ccu_id
                    LEFT JOIN ref.country country
                      ON country.iso2 = :country_iso2
                    LEFT JOIN customs.tariff_mapping mapping
                      ON mapping.candidate_id = candidate.candidate_id
                     AND mapping.country_id = country.country_id
                     AND mapping.record_status = 'ACTIVE'
                    WHERE {where_clause}
                    GROUP BY ccu.ccu_id
                    ORDER BY ccu.ccu_code
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
        )
        return total, items

    def ccu(self, *, ccu_code: str) -> dict[str, Any] | None:
        row = self._session.execute(
            text(
                """
                SELECT
                  ccu.ccu_code,
                  ccu.ccu_name_cn,
                  ccu.ccu_name_en,
                  parent.ccu_code AS parent_ccu_code,
                  ccu.vehicle_system,
                  ccu.unit_level::text AS unit_level,
                  ccu.function_description,
                  ccu.material_spec,
                  ccu.technical_qualifiers,
                  ccu.assembly_state::text AS assembly_state,
                  ccu.included_items,
                  ccu.excluded_items,
                  ccu.required_input_fields,
                  ccu.gri_2a_risk::text AS gri_2a_risk,
                  ccu.version,
                  ccu.verification_status::text AS verification_status
                FROM customs.customs_classification_unit ccu
                LEFT JOIN customs.customs_classification_unit parent
                  ON parent.ccu_id = ccu.parent_ccu_id
                WHERE ccu.ccu_code = :ccu_code
                  AND ccu.record_status = 'ACTIVE'
                """
            ),
            {"ccu_code": ccu_code},
        ).mappings().one_or_none()
        return dict(row) if row else None

    def ccu_tariff_options(
        self, *, ccu_code: str, country_iso2: str, as_of: date
    ) -> list[dict[str, Any]]:
        return self._rows(
            self._session.execute(
                text(
                    """
                    SELECT
                      candidate.candidate_rank,
                      candidate.hs_nomenclature_version,
                      candidate.hs6_code,
                      candidate.candidate_basis,
                      candidate.exclusion_notes,
                      candidate.verification_status::text AS candidate_verification_status,
                      mapping.mapping_id,
                      mapping.mapping_code,
                      mapping.tariff_version,
                      mapping.national_tariff_code,
                      mapping.tariff_description,
                      mapping.origin_regime::text AS origin_regime,
                      agreement.agreement_code,
                      mapping.duty_rate,
                      mapping.rate_type::text AS rate_type,
                      mapping.additional_measure,
                      mapping.eligibility_condition,
                      mapping.effective_from,
                      mapping.effective_to,
                      mapping.verification_status::text AS verification_status,
                      source.source_code,
                      source.canonical_url,
                      clause.locator_value AS source_locator
                    FROM customs.customs_classification_unit ccu
                    JOIN customs.ccu_candidate_hs candidate
                      ON candidate.ccu_id = ccu.ccu_id
                    JOIN customs.tariff_mapping mapping
                      ON mapping.candidate_id = candidate.candidate_id
                    JOIN ref.country country
                      ON country.country_id = mapping.country_id
                    LEFT JOIN ref.trade_agreement agreement
                      ON agreement.trade_agreement_id = mapping.trade_agreement_id
                    JOIN evidence.source_clause clause
                      ON clause.source_clause_id = mapping.source_clause_id
                    JOIN evidence.source_document source
                      ON source.source_document_id = clause.source_document_id
                    WHERE ccu.ccu_code = :ccu_code
                      AND country.iso2 = :country_iso2
                      AND ccu.record_status = 'ACTIVE'
                      AND mapping.record_status = 'ACTIVE'
                      AND mapping.effective_from <= :as_of
                      AND (mapping.effective_to IS NULL OR mapping.effective_to > :as_of)
                    ORDER BY
                      candidate.candidate_rank,
                      mapping.origin_regime,
                      agreement.agreement_code NULLS FIRST,
                      mapping.mapping_code
                    """
                ),
                {
                    "ccu_code": ccu_code,
                    "country_iso2": country_iso2.upper(),
                    "as_of": as_of,
                },
            )
        )
