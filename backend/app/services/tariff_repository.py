from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.calculation_engine import (
    EvidenceReference,
    TariffRateOption,
    VerificationStatus,
)


class TariffRepository:
    """Read-only version-aware tariff access.

    This repository returns every candidate. It deliberately does not choose a
    final classification when a CCU has multiple national tariff lines.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_effective_options(
        self,
        *,
        country_iso2: str,
        ccu_codes: tuple[str, ...],
        as_of: date,
    ) -> dict[str, dict[str, tuple[TariffRateOption, ...]]]:
        rows = self._session.execute(
            text(
                """
                SELECT
                  ccu.ccu_code,
                  mapping.mapping_code,
                  mapping.national_tariff_code,
                  mapping.duty_rate,
                  mapping.tariff_version,
                  mapping.effective_from,
                  mapping.effective_to,
                  mapping.verification_status::text AS verification_status,
                  mapping.additional_measure,
                  mapping.source_clause_id::text AS source_clause_id,
                  source.source_code,
                  clause.locator_value,
                  COALESCE(agreement.agreement_code, 'MFN') AS regime
                FROM customs.tariff_mapping mapping
                JOIN ref.country country
                  ON country.country_id = mapping.country_id
                JOIN customs.ccu_candidate_hs candidate
                  ON candidate.candidate_id = mapping.candidate_id
                JOIN customs.customs_classification_unit ccu
                  ON ccu.ccu_id = candidate.ccu_id
                JOIN evidence.source_clause clause
                  ON clause.source_clause_id = mapping.source_clause_id
                JOIN evidence.source_document source
                  ON source.source_document_id = clause.source_document_id
                LEFT JOIN ref.trade_agreement agreement
                  ON agreement.trade_agreement_id = mapping.trade_agreement_id
                WHERE country.iso2 = :country_iso2
                  AND ccu.ccu_code = ANY(:ccu_codes)
                  AND mapping.record_status = 'ACTIVE'
                  AND mapping.effective_from <= :as_of
                  AND (
                    mapping.effective_to IS NULL
                    OR mapping.effective_to > :as_of
                  )
                ORDER BY ccu.ccu_code, regime, mapping.mapping_code
                """
            ),
            {
                "country_iso2": country_iso2,
                "ccu_codes": list(ccu_codes),
                "as_of": as_of,
            },
        ).mappings()
        raw_rows = [dict(row) for row in rows]
        sst_by_ccu = self._unambiguous_sst_rates(raw_rows)
        result: dict[str, dict[str, list[TariffRateOption]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for row in raw_rows:
            measure = row["additional_measure"] or {}
            result[row["ccu_code"]][row["regime"]].append(
                TariffRateOption(
                    regime=row["regime"],
                    mapping_code=row["mapping_code"],
                    national_tariff_code=row["national_tariff_code"],
                    duty_rate=(
                        Decimal(str(row["duty_rate"])) if row["duty_rate"] is not None else None
                    ),
                    sst_rate=self._extract_sst_rate(measure) or sst_by_ccu.get(row["ccu_code"]),
                    verification_status=VerificationStatus(row["verification_status"]),
                    effective_from=row["effective_from"],
                    effective_to=row["effective_to"],
                    tariff_version=row["tariff_version"],
                    evidence=(
                        EvidenceReference(
                            source_clause_id=row["source_clause_id"],
                            source_code=row["source_code"],
                            locator=row["locator_value"],
                        ),
                    ),
                    classification_notes=measure.get("verification_scope"),
                )
            )
        return {
            ccu_code: {regime: tuple(options) for regime, options in regimes.items()}
            for ccu_code, regimes in result.items()
        }

    @staticmethod
    def require_explicit_selection(
        options: dict[str, dict[str, tuple[TariffRateOption, ...]]],
        selections: dict[str, dict[str, str]],
    ) -> dict[str, dict[str, TariffRateOption]]:
        selected: dict[str, dict[str, TariffRateOption]] = {}
        for ccu_code, regime_selections in selections.items():
            if ccu_code not in options:
                raise ValueError(f"No effective tariff options for {ccu_code}")
            selected[ccu_code] = {}
            for regime, mapping_code in regime_selections.items():
                candidates = options[ccu_code].get(regime, ())
                matches = [option for option in candidates if option.mapping_code == mapping_code]
                if len(matches) != 1:
                    raise ValueError(
                        f"Explicit mapping {mapping_code} is not a unique effective "
                        f"{regime} option for {ccu_code}"
                    )
                selected[ccu_code][regime] = matches[0]
        return selected

    @classmethod
    def _unambiguous_sst_rates(cls, rows: Sequence[Mapping[str, Any]]) -> dict[str, Decimal]:
        rates: dict[str, set[Decimal]] = defaultdict(set)
        for row in rows:
            if row["regime"] != "MFN":
                continue
            rate = cls._extract_sst_rate(row["additional_measure"] or {})
            if rate is not None:
                rates[row["ccu_code"]].add(rate)
        return {
            ccu_code: next(iter(values)) for ccu_code, values in rates.items() if len(values) == 1
        }

    @staticmethod
    def _extract_sst_rate(measure: dict[str, Any]) -> Decimal | None:
        value = measure.get("sst_display_rate")
        if value is None and isinstance(measure.get("sst"), dict):
            value = measure["sst"].get("displayed_rate")
        return Decimal(str(value)) if value is not None else None
