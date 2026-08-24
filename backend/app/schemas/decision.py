from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


Powertrain = Literal[
    "ICE_GASOLINE",
    "ICE_DIESEL",
    "HEV",
    "PHEV",
    "EREV",
    "BEV",
    "FCEV",
    "OTHER",
]


class RouteResolveRequest(BaseModel):
    as_of: date
    facts: dict[str, Any] = Field(default_factory=dict)


class DecisionProjectCreate(BaseModel):
    enterprise_code: str = Field(min_length=1, max_length=120)
    project_code: str = Field(min_length=1, max_length=120)
    project_name: str = Field(min_length=1, max_length=240)
    country_iso2: str = Field(default="MY", min_length=2, max_length=2)
    calculation_date: date
    model_code: str = Field(min_length=1, max_length=120)
    vehicle_type: str = Field(default="PASSENGER_VEHICLE", max_length=120)
    powertrain: Powertrain
    technical_attributes: dict[str, Any] = Field(default_factory=dict)


class ProjectRouteFactsUpdate(BaseModel):
    facts: dict[str, Any]


class ProjectInputUpdate(BaseModel):
    value_payload: Any
    provided_by: str = Field(min_length=1, max_length=160)
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str | None = None


class ProjectApprovalUpdate(BaseModel):
    approval_reference: str | None = None
    approval_status: Literal[
        "NOT_PROVIDED", "PROVIDED", "VERIFIED", "REJECTED", "EXPIRED"
    ] = "NOT_PROVIDED"
    authority_name: str | None = None
    issue_date: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    covered_model: str | None = None
    covered_tariff_codes: list[str] = Field(default_factory=list)
    approved_rate: str | None = None
    exemption_scope: dict[str, Any] = Field(default_factory=dict)
    evidence_ref: str | None = None
    notes: str | None = None


class ProjectTariffSelectionUpdate(BaseModel):
    tariff_mapping_id: str | None = None
    vehicle_tariff_rate_line_id: str | None = None
    selected_by: str = Field(min_length=1, max_length=160)
    selection_note: str | None = None


class ProjectBomLineUpdate(BaseModel):
    enterprise_part_no: str = Field(min_length=1, max_length=160)
    part_name: str | None = Field(default=None, max_length=240)
    ccu_code: str = Field(pattern=r"^CCU-[A-Z0-9-]+$")
    bucket_code: str | None = None
    customs_value: Decimal = Field(ge=0)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    currency_code: str = Field(default="MYR", pattern=r"^[A-Z]{3}$")
    origin_country_iso2: str = Field(default="CN", min_length=2, max_length=2)
    local_or_imported: Literal["IMPORTED", "LOCAL"] = "IMPORTED"
    enterprise_inputs_complete: bool = False
    gri_2a_review_complete: bool = False
    notes: str | None = None


class ProjectBomMappingSelectionUpdate(BaseModel):
    mapping_code: str = Field(min_length=1, max_length=200)
    selected_by: str = Field(min_length=1, max_length=160)
    selection_note: str | None = None


class ProjectBomComparisonRequest(BaseModel):
    requested_regimes: tuple[Literal["MFN", "ACFTA", "RCEP"], ...] = (
        "MFN",
        "ACFTA",
        "RCEP",
    )
    eligibility: dict[str, dict[str, bool]] = Field(default_factory=dict)
    sales_revenue: Decimal | None = Field(default=None, ge=0)
    non_import_costs: Decimal | None = Field(default=None, ge=0)
    recoverable_sst_fraction: Decimal = Field(default=Decimal("0"), ge=0, le=1)


class CbuCalculateRequest(BaseModel):
    """CBU 整车进口税务计算请求 —— 用户只需提供车辆基本属性,系统自动解析HS/PDK税号。"""

    effective_date: date
    origin_country_iso2: str = Field(default="CN", min_length=2, max_length=2)
    powertrain: Powertrain
    displacement_cc: int | None = Field(
        default=None, ge=0, description="排量(cc), ICE/HEV/PHEV/EREV 建议填写"
    )
    body_type: Literal["SEDAN", "SUV", "MPV", "HATCHBACK", "COUPE", "WAGON", "OTHER"] = "SEDAN"
    drive_type: Literal["2WD", "4WD_AWD"] = "4WD_AWD"
    customs_value: Decimal | None = Field(
        default=None, ge=0, description="海关价值(MYR), 留空则使用标准化税基100"
    )
    selected_policy_codes: list[str] = Field(
        default_factory=list, description="用户申报已取得的优惠政策代码"
    )


# ── CKD ─────────────────────────────────────────────────────────────


class ClassificationEvidence(BaseModel):
    """海关归类依据——WITH_RULING时必填。"""
    basis: Literal[
        "CUSTOMS_RULING", "APPROVED_DECLARATION",
        "TARIFF_SCHEDULE_MATCH", "USER_ASSERTED",
    ]
    reference_no: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


CkdDeclarationMode = Literal[
    "CKD_WHOLE_KIT_WITH_RULING",
    "CKD_WHOLE_KIT_PENDING_RULING",
    "CLASSIFICATION_PENDING",
]


class CkdCalculateRequest(BaseModel):
    """CKD 整套散件进口+本地组装税务计算请求。

    与 CBU 的本质区别：
    - CKD 税号需用户确认（需已有海关归类裁定或 MITI CKD AP）
    - 消费税和成车销售税不在进口环节征收，在本地组装后按核定价值征收
    - 全流程模拟需要用户提供消费税/销售税的核定价值系数
    - MITI CKD AP ≠ 税收优惠，只是进口许可证
    """

    effective_date: date
    origin_country_iso2: str = Field(default="CN", min_length=2, max_length=2)
    powertrain: Powertrain
    displacement_cc: int | None = Field(
        default=None, ge=0, description="排量(cc), ICE/HEV/PHEV/EREV 建议填写"
    )
    body_type: Literal["SEDAN", "SUV", "MPV", "HATCHBACK", "COUPE", "WAGON", "OTHER"] = "SEDAN"
    drive_type: Literal["2WD", "4WD_AWD"] = "4WD_AWD"
    # CKD 税号：WITH_RULING 必填；PENDING_RULING 可选；CLASSIFICATION_PENDING 留空
    ckd_tariff_code: str | None = Field(
        default=None, pattern=r"^\d{10}$",
        description="CKD PDK税号（10位），已取得归裁定时必填",
    )
    classification_evidence: ClassificationEvidence | None = None
    customs_value: Decimal | None = Field(
        default=None, ge=0, description="CKD套件海关价值(MYR), 留空则使用标准化税基100"
    )
    declaration_mode: CkdDeclarationMode = "CKD_WHOLE_KIT_PENDING_RULING"
    # MITI CKD AP — 进口许可，不等同于税务减免
    miti_ckd_ap_confirmed: bool = Field(default=False)
    # 用户确认的优惠政策代码
    selected_policy_codes: list[str] = Field(default_factory=list)
    # 全流程模拟系数 — 仅当对应税率 > 0 时需要
    excise_value_ratio: Decimal | None = Field(
        default=None, ge=0, description="消费税核定价值 ÷ 进口价值"
    )
    sales_value_ratio: Decimal | None = Field(
        default=None, ge=0, description="销售税计税价值 ÷ 进口价值"
    )


class QuickEstimateRequest(BaseModel):
    country_iso2: str = Field(default="MY", min_length=2, max_length=2)
    origin_country_iso2: str = Field(default="CN", min_length=2, max_length=2)
    effective_date: date
    path: Literal["AUTO", "CBU", "CKD"] = "AUTO"
    powertrain: Powertrain = "BEV"
    cbu_tariff_code: str | None = Field(default=None, pattern=r"^\d{6,10}$")
    ckd_declaration_mode: Literal["WHOLE_KIT", "PARTS_BOM"] = "WHOLE_KIT"
    ckd_tariff_code: str | None = Field(default=None, pattern=r"^\d{6,10}$")
    customs_value_cbu: Decimal | None = Field(default=None, gt=0)
    customs_value_ckd: Decimal | None = Field(default=None, gt=0)
    # Vietnam CKD major-parts estimate: a national tariff line must be explicitly
    # selected per component.  The service must never infer the line by choosing
    # the lowest rate from a broad HS6 candidate set.
    ckd_component_tariff_codes: dict[str, str] = Field(default_factory=dict)
