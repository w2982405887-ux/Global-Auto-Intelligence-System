const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

// The backend uses a double-submit CSRF token: the value returned by
// /auth/me (preferred) or a readable csrf cookie is echoed in X-CSRF-Token.
// Keeping the preferred value in module memory avoids putting it in local
// storage while still allowing a fresh page to use the cookie fallback.
let csrfTokenMemory: string | null | undefined;

export function setCsrfToken(value: string | null | undefined) {
  csrfTokenMemory = value;
}

function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const names = ["gais_csrf", "csrf_token", "csrf-token", "XSRF-TOKEN"];
  for (const cookie of document.cookie.split(";")) {
    const [rawName, ...rawValue] = cookie.trim().split("=");
    if (names.includes(rawName) && rawValue.length > 0) {
      return decodeURIComponent(rawValue.join("="));
    }
  }
  return null;
}

export function getCsrfToken(): string | null {
  if (csrfTokenMemory !== undefined) return csrfTokenMemory;
  return readCsrfCookie();
}

export function getCsrfHeaders(): Record<string, string> {
  const value = getCsrfToken();
  return value ? { "X-CSRF-Token": value } : {};
}

export type VerificationStatus =
  | "UNVERIFIED"
  | "CANDIDATE"
  | "VERIFIED"
  | "RULING_CONFIRMED";

export type SourceReferenceFields = {
  source_id?: string;
  document_title?: string;
  authority_name?: string;
  document_number?: string | null;
  source_type?: string;
  official_url?: string | null;
  locator?: { locator_type?: string; locator_value?: string };
  original_excerpt?: string | null;
  translated_excerpt_cn?: string | null;
  evidence_summary?: string | null;
};

export type RecentPolicy = {
  rule_code: string;
  iso2: string;
  country_name_cn: string;
  rule_name_cn: string;
  rule_domain: string;
  verification_status: VerificationStatus;
  effective_from: string;
  effective_to: string | null;
  rule_content?: string | null;
  condition_expression?: Record<string, unknown> | null;
  benefit_expression?: Record<string, unknown> | null;
  approval_required?: boolean | null;
  incentive_scope?: string | null;
  import_mode?: string | null;
  powertrain?: string | null;
  source_type?: string | null;
  document_number?: string | null;
  authority_name?: string | null;
  locator_type?: string | null;
  // Backend may send these as top-level or nested
  source_code?: string;
  document_title?: string;
  source_locator?: string;
  canonical_url?: string | null;
  policy_stage?: "CURRENT" | "FUTURE" | "EXPIRING" | "EXPIRED_RECENT";
  policy_category?:
    | "TAX"
    | "FTA_ORIGIN"
    | "ACCESS_APPROVAL"
    | "INCENTIVE_LOCALIZATION"
    | "CLASSIFICATION"
    | "STRATEGY";
  impact_scope?: "CBU" | "CKD" | "BOTH";
  business_impact?: "HIGH" | "MEDIUM" | "LOW";
  freshness_status?: "RECENT" | "STALE" | "UNVERIFIED";
  updated_at?: string | null;
  last_verified_at?: string | null;
  // Unified — prefer this when present
  source_reference?: SourceReferenceFields | null;
};

export type PolicyHighlight = {
  rule_code: string;
  rule_name_cn: string;
  rule_domain: string;
  verification_status: VerificationStatus;
  effective_from: string;
  effective_to: string | null;
  updated_at: string | null;
  source_id: string;
  document_title: string;
  document_number: string | null;
  source_type: string;
  official_url: string | null;
  authority_name: string;
  locator_type: string;
  source_locator: string;
};

export type DashboardOverview = {
  as_of: string;
  connected_country_count: number;
  rule_count: number;
  special_policy_count: number;
  active_special_policy_count: number;
  pending_review_policy_count: number;
  source_count: number;
  ccu_count: number;
  ccu_tariff_mapping_count: number;
  vehicle_tariff_line_count: number;
  open_missing_data: number;
  future_effective_count: number;
  last_updated_at: string | null;
  recent_policies: RecentPolicy[];
};

export type RouteReadiness = {
  decision_order: number;
  route_code: string;
  route_name_cn: string;
  route_verification_status: VerificationStatus;
  tariff_line_count: number;
  mfn_line_count: number;
  acfta_line_count: number;
  rcep_line_count: number;
  missing_public_duty_rate_count: number;
  verified_tariff_line_count: number;
  kd_tax_bucket_count: number;
  active_ccu_count: number;
  mapped_ccu_count: number;
  ccu_tariff_mapping_count: number;
  ccu_mapping_missing_duty_count: number;
  completeness_percent: number;
};

export type CountryOverview = {
  country: {
    iso2: string;
    iso3: string;
    name_cn: string;
    name_en: string;
    currency_code: string;
    timezone_name: string;
  };
  as_of: string;
  route_readiness: RouteReadiness[];
  policy_nodes: {
    statistics: {
      current: number;
      future_effective: number;
      expiring: number;
    };
    highlights: PolicyHighlight[];
  };
  open_missing_data: number;
  completeness_percent: number;
  last_verified_at: string | null;
};

export type TaxRoute = {
  decision_order: number;
  route_code: string;
  route_name_cn: string;
  route_name_en: string;
  route_kind: string;
  import_mode: string;
  classification_granularity: string;
  decision_condition: Record<string, unknown>;
  required_input_fields: string[];
  fallback_route_code: string | null;
  decision_note: string;
  effective_from: string;
  effective_to: string | null;
  verification_status: VerificationStatus;
};

export type TaxRouteResponse = {
  country_iso2: string;
  as_of: string;
  items: TaxRoute[];
};

export type DecisionProject = {
  project_id: string;
  project_code: string;
  enterprise_code: string;
  project_name: string;
  country_iso2: string;
  country_name_cn: string;
  origin_country_iso2: string;
  calculation_date: string;
  selected_route_code: string | null;
  route_facts: Record<string, unknown>;
  verification_status: VerificationStatus;
  record_status: string;
  model_code: string;
  vehicle_type: string;
  powertrain: string;
};

export type RouteResolution = {
  selected_route_code: string | null;
  verification_status: VerificationStatus;
  required_input_fields: string[];
  fallback_route_code: string | null;
  matched_route_codes: string[];
  resolution_status: "RESOLVED" | "NO_MATCH" | "AMBIGUOUS";
};

export type ProjectInput = {
  field_path: string;
  value_payload: unknown;
  value_status: "EMPTY" | "PROVIDED" | "VERIFIED" | "REJECTED";
  evidence_refs: string[];
  notes: string | null;
};

export type ProjectCompletion = {
  project_id: string;
  project_code: string;
  selected_route_code: string | null;
  required_count: number;
  accepted_required_count: number;
  missing_required_count: number;
  completion_ratio: string;
  ready_for_preview: boolean;
};

export type ApprovalRequirement = {
  requirement_code: string;
  requirement_type: "MANDATORY" | "INCENTIVE_ONLY" | string;
  applicable_object: string;
  import_mode: string | null;
  powertrain: string | null;
  required_document: string[];
  failure_consequence: string;
  verification_status: VerificationStatus;
  authority_name: string | null;
  source_code: string;
  canonical_url: string | null;
  approval_reference: string | null;
  approval_status:
    | "NOT_PROVIDED"
    | "PROVIDED"
    | "VERIFIED"
    | "REJECTED"
    | "EXPIRED"
    | null;
};

export type ApprovalReadiness = {
  items: ApprovalRequirement[];
  mandatory_count: number;
  missing_mandatory_count: number;
  missing_requirement_codes: string[];
  ready_for_preview: boolean;
};

export type VehicleTariffOption = {
  vehicle_tariff_rate_line_id: string;
  route_code: string;
  tariff_schedule_code: string;
  origin_regime: string;
  agreement_code: string | null;
  hs6_code: string;
  national_tariff_code: string;
  tariff_description: string;
  powertrain: string;
  import_duty_rate: string | null;
  sales_tax_rate: string | null;
  excise_duty_rate: string | null;
  verification_status: VerificationStatus;
  source_code: string;
  source_locator: string;
};

export type QuickEstimateScenario = {
  name: string;
  regime: string | null;
  base_value: string | null;
  import_duty_rate?: string | null;
  excise_duty_rate?: string | null;
  sales_tax_rate?: string | null;
  known_tax_amount: string | null;
  effective_tax_rate: string | null;
  tax_lines: Array<{
    tax: string;
    base: string;
    rate: string | null;
    amount: string | null;
    formula: string;
    scope_note?: string | null;
  }>;
    unknown_tax_items: string[];
    is_complete_statutory_chain: boolean;
    matched_component_count?: number;
    expected_component_count?: number;
  };

export type QuickEstimatePath = {
  path: "CBU" | "CKD";
  route_code: string;
  status: string;
  confidence: "LOW" | "MEDIUM" | "HIGH";
  classification_scope?: {
    status: string;
    candidate_scope: string;
    final_national_tariff_code: string | null;
    required_facts: string[];
  };
  matched_tariff?: {
    national_tariff_code: string;
    hs6_code: string;
    description: string;
    verification_status: VerificationStatus;
    source_code: string;
    source_locator: string;
  } | null;
  candidate_tariffs: Array<{
    regime: string;
    national_tariff_code: string;
    import_duty_rate: string | null;
    excise_duty_rate: string | null;
    sales_tax_rate: string | null;
    verification_status: VerificationStatus;
  }>;
  component_candidates?: Array<{
    ccu_code: string;
    ccu_name_cn: string;
    required_facts: string[];
    candidates: Array<{
      agreement: string;
      national_tariff_code: string;
      tariff_description: string;
      import_duty_rate: string | null;
      verification_status: VerificationStatus;
    }>;
  }>;
  statutory: QuickEstimateScenario;
  incentive: QuickEstimateScenario;
  policy_matches?: QuickPolicyMatch[];
  tax_chain?: TaxChainSummary;
  missing_items: string[];
  dependency_level: string;
  recommended_use: string;
};

export type QuickPolicyMatch = {
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
  description?: string | null;
  condition_expression?: Record<string, unknown> | null;
  benefit_expression?: Record<string, unknown> | null;
  effective_from?: string | null;
  effective_to?: string | null;
  source_reference?: SourceReferenceFields | null;
};

export type TaxChainNode = {
  stage_code: string;
  stage_name: string;
  status: string;
  known_tax_amount: string | null;
  known_effective_rate: string | null;
  recoverability: string;
  tax_lines: Array<{
    tax: string;
    base: string | null;
    rate: string | null;
    amount: string | null;
    formula: string;
    status?: string;
    scope_note?: string | null;
  }>;
  missing_fields: string[];
  note?: string;
};

export type TaxChainSummary = {
  version: string;
  status: string;
  classification_route: string;
  powertrain: string;
  base_value: string | null;
  known_tax_amount: string | null;
  known_effective_rate: string | null;
  cash_tax_outlay: string | null;
  non_recoverable_tax_rate: string | null;
  unknown_tax_items: string[];
  assumptions: string[];
  nodes: TaxChainNode[];
};

export type ResolvedPolicyView = {
  program_code: string;
  program_name_cn: string;
  status: string;
  status_chain?: string[];
  matched_conditions?: string[];
  required_documents?: string[];
  approval_authority?: string | null;
  incentive_scope?: string | null;
  condition_expression?: Record<string, unknown> | null;
  benefit_expression?: Record<string, unknown> | null;
  effective_from?: string | null;
  effective_to?: string | null;
  benefit?: {
    benefit_type?: string;
    target_taxes?: string[];
    overrides?: Record<string, string>;
    requires_project_approval?: boolean;
    note?: string | null;
  } | null;
  source_reference?: SourceReferenceFields | null;
};

export type IncentiveValidation = {
  resolved: ResolvedPolicyView[];
  invalid_codes?: string[];
  notes?: string[];
  valid?: string[];
  invalid?: string[];
  expired?: string[];
  powertrain_mismatch?: string[];
  import_mode_mismatch?: string[];
};

export type QuickEstimateResult = {
  country_iso2: string;
  country_name_cn: string;
  effective_date: string;
  powertrain: string;
  requested_path: "AUTO" | "CBU" | "CKD";
  estimate_level: "QUICK_ESTIMATE" | "ENTERPRISE_ESTIMATE";
  recommendation: {
    recommended_path: "CBU" | "CKD" | null;
    statutory_rate_advantage: string | null;
    confidence: "LOW" | "MEDIUM" | "HIGH";
    summary: string;
    largest_uncertainty: string;
  };
  paths: QuickEstimatePath[];
  policy_matches?: QuickPolicyMatch[];
  assumptions: Array<{
    condition: string;
    treatment: string;
    kind: string;
  }>;
  disclaimer: string;
};

export type CalculationMissingItem = {
  field_path: string;
  description: string;
  data_owner: string;
  data_kind: string;
  data_ownership: string;
  blocking_scope: string;
  priority: string;
  next_action: string;
  return_step?: number;
  status?: string;
};

export type CalculationLine = {
  sequence_no: number;
  tax_code: string;
  base_amount: string;
  rate: string;
  amount: string;
  display_formula?: string;
  national_tariff_code?: string;
  rate_line_code?: string;
  verification_status?: VerificationStatus;
  source?: {
    source_code: string;
    source_locator: string;
    source_clause_id: string;
  };
  notes?: string;
};

export type ProjectCalculationPreview = {
  project_id: string;
  project_code: string;
  route_code: string;
  route_name: string;
  calculation_date: string;
  currency_code: string;
  engine_version: string;
  status: "COMPLETE" | "PARTIAL" | "BLOCKED";
  calculation_scope: string;
  totals: {
    customs_value: string;
    gross_tax: string;
    recoverable_tax: string;
    net_tax: string;
    effective_tax_rate: string;
    landed_value_before_other_costs: string;
  } | null;
  lines: CalculationLine[];
  missing_data: CalculationMissingItem[];
  warnings: string[];
  operational_use_permitted: boolean;
};

export type CalculationRunDetail = {
  run: {
    calculation_run_id: string;
    run_code: string;
    engine_version: string;
    run_status: string;
    completeness: string;
    currency_code: string;
    base_value: string;
    gross_tax: string;
    recoverable_tax: string;
    net_tax: string;
    effective_tax_rate: string;
    rule_snapshot_at: string;
    completed_at: string;
    project_code: string;
    project_name: string;
    route_code: string;
    route_name_cn: string;
  };
  lines: CalculationLine[];
};

export type DecisionTraceItem = {
  sequence_no: number;
  step_type: string;
  decision_question: string;
  explicit_rationale: string;
  result: Record<string, unknown>;
  confidence: string;
  human_review_required: boolean;
  source_clause_refs: Array<Record<string, string>>;
};

export type CcuCatalogItem = {
  ccu_code: string;
  ccu_name_cn: string;
  vehicle_system: string;
  verification_status: VerificationStatus;
};

export type CcuTariffOption = {
  mapping_id: string;
  mapping_code: string;
  origin_regime: string;
  agreement_code: string | null;
  national_tariff_code: string;
  duty_rate: string | null;
  sst_rate: string | null;
  verification_status: VerificationStatus;
};

export type ProjectBomLine = {
  project_bom_line_id: string;
  line_no: number;
  enterprise_part_no: string;
  part_name: string | null;
  ccu_code: string;
  ccu_name_cn: string;
  vehicle_system: string;
  bucket_code: string | null;
  customs_value: string;
  quantity: string;
  currency_code: string;
  origin_country_iso2: string;
  local_or_imported: "IMPORTED" | "LOCAL";
  enterprise_inputs_complete: boolean;
  gri_2a_review_complete: boolean;
  selections: Record<
    string,
    {
      tariff_mapping_id: string;
      mapping_code: string;
      national_tariff_code: string;
      duty_rate: string | null;
      verification_status: VerificationStatus;
    }
  >;
};

export type ProjectBomResponse = {
  project_id: string;
  project_code: string;
  currency_code: string;
  items: ProjectBomLine[];
  summary: {
    line_count: number;
    imported_line_count: number;
    local_line_count: number;
    imported_customs_value: string;
  };
};

export type BomComparisonScenario = {
  requested_regime: string;
  applied_regime: string;
  fallback_applied: boolean;
  completeness: "COMPLETE" | "PARTIAL" | "BLOCKED";
  customs_value: string;
  gross_import_tax: string | null;
  net_import_tax: string | null;
  effective_net_tax_rate: string | null;
  landed_cost: string | null;
  gross_profit: string | null;
  lines: Array<{
    ccu_code: string;
    mapping_code: string;
    national_tariff_code: string;
    duty_rate: string;
    import_duty: string;
    sst_rate: string;
    sst_amount: string;
    net_import_tax: string;
  }>;
  missing_data: CalculationMissingItem[];
  warnings: string[];
};

export type BomComparisonResult = {
  baseline_regime: string;
  currency_code: string;
  scenarios: BomComparisonScenario[];
  decision_summary: {
    lowest_net_tax_requested_regime: string | null;
    highest_profit_requested_regime: string | null;
    all_results_operationally_complete: boolean;
    engine_version: string;
    warning: string;
  };
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    const method = (init?.method ?? "GET").toUpperCase();
    const headers = new Headers(init?.headers);
    const isMutation = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
    const authPath = path.split("?", 1)[0];
    // Login and registration establish the session and therefore cannot
    // require a CSRF token from a session that does not exist yet.  The
    // backend still applies its own credential and rate-limit checks.
    const isSessionBootstrap = ["/auth/dev/login", "/auth/local-login", "/auth/login", "/auth/register"].includes(authPath);
    if (isMutation && !isSessionBootstrap) {
      const token = getCsrfToken();
      if (token) headers.set("X-CSRF-Token", token);
    }
    return await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      // Authentication is held in an HttpOnly server-session cookie.  Keep
      // this at the single API boundary so every current and future private
      // request sends the cookie consistently.
      credentials: init?.credentials ?? "include",
    });
  } catch (cause) {
    if (init?.signal?.aborted) {
      throw new DOMException("The operation was aborted.", "AbortError");
    }
    if (cause instanceof DOMException && cause.name === "AbortError") {
      throw cause;
    }
    throw new ApiError(
      `暂时无法连接后端服务（${API_BASE_URL}）。服务可能正在重启，请稍后重新提交。`,
      0,
    );
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await apiFetch(path, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new ApiError(`API请求失败：${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

async function writeRequest<T>(
  path: string,
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  payload?: unknown,
): Promise<T> {
  const response = await apiFetch(path, {
    method,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorPayload = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new ApiError(
      errorPayload?.detail ?? `API请求失败：${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export function getDashboardOverview(signal?: AbortSignal) {
  return request<DashboardOverview>("/dashboard/overview", signal);
}

// ── Authentication / organization context ─────────────────────────

export type AuthUser = {
  user_id: string;
  email: string | null;
  full_name: string | null;
  avatar_url?: string | null;
  status?: string;
};

export type Organization = {
  organization_id: string;
  organization_code?: string | null;
  name: string;
  display_name?: string | null;
  role?: string | null;
  membership_id?: string | null;
  status?: string;
};

export type AuthConfig = {
  oidc_enabled: boolean;
  oidc_provider_name?: string | null;
  dev_login_enabled: boolean;
  dev_login_label?: string | null;
  /** Personal email/password accounts. Enabled by default in the standalone app. */
  personal_login_enabled?: boolean;
  personal_login_label?: string | null;
};

export type AuthMeResponse = {
  authenticated: boolean;
  user: AuthUser | null;
  organizations: Organization[];
  active_organization: Organization | null;
  permissions: string[];
  csrf_token?: string | null;
  auth_config?: Partial<AuthConfig> | null;
};

export function getAuthMe(signal?: AbortSignal) {
  return request<AuthMeResponse>("/auth/me", signal);
}

export function getAuthConfig(signal?: AbortSignal) {
  return request<AuthConfig>("/auth/config", signal);
}

export function logout() {
  return writeRequest<{ ok: boolean }>("/auth/logout", "POST");
}

export type PersonalAccountCredentials = {
  email: string;
  password: string;
};

export type PersonalAccountRegistration = PersonalAccountCredentials & {
  display_name: string;
};

/** Sign in to a personal account and return the authenticated session. */
export function login(payload: PersonalAccountCredentials) {
  return writeRequest<AuthMeResponse>("/auth/login", "POST", payload);
}

/** Create a personal account, sign it in, and return the authenticated session. */
export function register(payload: PersonalAccountRegistration) {
  return writeRequest<AuthMeResponse>("/auth/register", "POST", payload);
}

export function devLogin(payload?: { email?: string; display_name?: string }) {
  return writeRequest<AuthMeResponse>("/auth/dev/login", "POST", payload);
}

export function switchOrganization(organizationId: string) {
  return writeRequest<{ active_organization?: Organization; organization_id?: string }>(
    `/organizations/${encodeURIComponent(organizationId)}/switch`,
    "POST",
  );
}

export type OrganizationMember = {
  membership_id: string;
  user_id: string;
  email: string | null;
  display_name: string | null;
  status: "ACTIVE" | "SUSPENDED" | string;
  role_codes: string[];
};

export type OrganizationMembersResponse = {
  organization_id: string;
  items: OrganizationMember[];
};

export function getOrganizationMembers(organizationId: string, signal?: AbortSignal) {
  return request<OrganizationMembersResponse>(
    `/organizations/${encodeURIComponent(organizationId)}/members`,
    signal,
  );
}

export function inviteOrganizationMember(
  organizationId: string,
  payload: { email: string; role_code: string; expires_in_days?: number },
) {
  return writeRequest<{
    invitation: { id: string; email: string; role_code: string; status: string; expires_at: string };
    invitation_token: string;
  }>(
    `/organizations/${encodeURIComponent(organizationId)}/members/invitations`,
    "POST",
    payload,
  );
}

export function updateOrganizationMember(
  organizationId: string,
  membershipId: string,
  payload: { role_codes: string[]; status?: "ACTIVE" | "SUSPENDED" },
) {
  return writeRequest<{
    status: string;
    membership_id: string;
    role_codes: string[];
  }>(
    `/organizations/${encodeURIComponent(organizationId)}/members/${encodeURIComponent(membershipId)}`,
    "PATCH",
    payload,
  );
}

export function getCountryOverview(iso2: string, signal?: AbortSignal) {
  return request<CountryOverview>(`/countries/${iso2}/overview`, signal);
}

export function getCountryTaxRoutes(iso2: string, signal?: AbortSignal) {
  return request<TaxRouteResponse>(`/countries/${iso2}/tax-routes`, signal);
}

export function createDecisionProject(payload: {
  enterprise_code: string;
  project_code: string;
  project_name: string;
  country_iso2: string;
  calculation_date: string;
  model_code: string;
  vehicle_type: string;
  powertrain: string;
  technical_attributes: Record<string, unknown>;
}) {
  return writeRequest<DecisionProject>("/projects", "POST", payload);
}

export function updateProjectRouteFacts(
  projectId: string,
  facts: Record<string, unknown>,
) {
  return writeRequest<{
    project: DecisionProject;
    resolution: RouteResolution;
  }>(`/projects/${projectId}/route-facts`, "PUT", { facts });
}

export function getProjectInputs(projectId: string) {
  return request<{ project_id: string; items: ProjectInput[] }>(
    `/projects/${projectId}/inputs`,
  );
}

export function setProjectInput(
  projectId: string,
  fieldPath: string,
  valuePayload: unknown,
) {
  return writeRequest<{ completion: ProjectCompletion }>(
    `/projects/${projectId}/inputs/${encodeURIComponent(fieldPath)}`,
    "PUT",
    {
      value_payload: valuePayload,
      provided_by: "frontend-demo-user",
      evidence_refs: [],
    },
  );
}

export function getProjectCompletion(projectId: string) {
  return request<ProjectCompletion>(`/projects/${projectId}/completion`);
}

export function getApprovalReadiness(projectId: string) {
  return request<ApprovalReadiness>(
    `/projects/${projectId}/approval-readiness`,
  );
}

export function saveProjectApproval(
  projectId: string,
  requirementCode: string,
  payload: {
    approval_reference: string | null;
    approval_status: string;
  },
) {
  return writeRequest<{ readiness: ApprovalReadiness }>(
    `/projects/${projectId}/approvals/${requirementCode}`,
    "PUT",
    payload,
  );
}

export function getVehicleTariffOptions(
  countryIso2: string,
  routeCode: string,
  powertrain: string,
  asOf: string,
) {
  const query = new URLSearchParams({
    route_code: routeCode,
    powertrain,
    as_of: asOf,
    origin_regime: "MFN",
    limit: "100",
  });
  return request<{ total: number; items: VehicleTariffOption[] }>(
    `/countries/${countryIso2}/vehicle-tariffs?${query.toString()}`,
  );
}

export function saveTariffSelection(
  projectId: string,
  vehicleTariffRateLineId: string,
) {
  return writeRequest<{ project_tariff_selection_id: string }>(
    `/projects/${projectId}/tariff-selections/vehicle`,
    "PUT",
    {
      vehicle_tariff_rate_line_id: vehicleTariffRateLineId,
      selected_by: "frontend-demo-user",
      selection_note: "用户在五路径向导中显式选择",
    },
  );
}

export function getCcuCatalog(query = "") {
  const params = new URLSearchParams({ country: "MY", limit: "100" });
  if (query) params.set("query", query);
  return request<{ total: number; items: CcuCatalogItem[] }>(
    `/ccus?${params.toString()}`,
  );
}

export function createQuickEstimate(payload: {
  country_iso2: string;
  origin_country_iso2: string;
  effective_date: string;
  path: "AUTO" | "CBU" | "CKD";
  powertrain: string;
  cbu_tariff_code?: string | null;
  ckd_declaration_mode: "WHOLE_KIT" | "PARTS_BOM";
  ckd_tariff_code?: string | null;
  customs_value_cbu?: string | null;
  customs_value_ckd?: string | null;
  ckd_component_tariff_codes?: Record<string, string>;
}) {
  return writeRequest<QuickEstimateResult>(
    "/quick-estimates",
    "POST",
    payload,
  );
}

// ── Shared treatment type ──────────────────────────────────────────

export type ResolvedTreatment = {
  tax_code: string;
  stage: string;
  statutory_rate: string | null;
  applied_rate: string | null;
  treatment: string;
  is_conditional: boolean;
  approval_required: boolean;
  approval_confirmed: boolean;
  source_policy_code: string | null;
  source_reference?: SourceReferenceFields | null;
  note: string;
};

// ── CBU Calculator ─────────────────────────────────────────────────

export type CbuImportDutyOption = {
  regime: string;
  agreement_code: string | null;
  national_tariff_code: string;
  tariff_description: string;
  rate: string | null;
  per_100: string | null;
  verification_status: VerificationStatus;
  eligibility_note: string | null;
  rule_reference?: { rule_id?: string | null; rule_type?: string | null; rule_description?: string | null };
  source_reference?: { source_id?: string; document_title?: string; authority_name?: string; document_number?: string | null; source_type?: string; official_url?: string | null; locator?: { locator_type?: string; locator_value?: string } };
};

export type CbuCombinedResult = {
  regime_label: string;
  agreement_code: string | null;
  import_duty_rate: string | null;
  import_duty_per_100: string | null;
  excise_duty_rate: string | null;
  excise_duty_per_100: string | null;
  sales_tax_rate: string | null;
  sales_tax_per_100: string | null;
  total_per_100: string | null;
  effective_tax_rate: string | null;
  is_complete: boolean;
  unknown_items: string[];
};

export type CbuCalculationResult = {
  country_iso2: string;
  effective_date: string;
  powertrain: string;
  displacement_cc: number | null;
  origin_country_iso2: string;
  normalized_base: string;
  hs_classification: {
    national_tariff_code: string;
    hs6_code: string;
    tariff_description: string;
    verification_status: VerificationStatus;
    source_code: string;
    source_locator: string;
  } | null;
  import_duty_options: CbuImportDutyOption[];
  excise_duty: ResolvedTreatment;
  sales_tax: ResolvedTreatment;
  combined_results: CbuCombinedResult[];
  incentive_validation?: IncentiveValidation | null;
  notes: string[];
  disclaimer: string;
};

export function calculateCbu(payload: {
  effective_date: string;
  origin_country_iso2: string;
  powertrain: string;
  displacement_cc?: number | null;
  body_type?: string;
  drive_type?: string;
  customs_value?: string | null;
  selected_policy_codes?: string[];
}) {
  return writeRequest<CbuCalculationResult>("/cbu/calculate", "POST", payload);
}

// ── CKD Calculator ─────────────────────────────────────────────────

export type CkdImportDutyOption = {
  regime: string;
  agreement_code: string | null;
  national_tariff_code: string;
  tariff_description: string;
  rate: string | null;
  per_100: string | null;
  verification_status: VerificationStatus;
  eligibility_note: string | null;
  rule_reference?: { rule_id?: string | null; rule_type?: string | null; rule_description?: string | null };
  source_reference?: { source_id?: string; document_title?: string; authority_name?: string; document_number?: string | null; source_type?: string; official_url?: string | null; locator?: { locator_type?: string; locator_value?: string } };
};

export type CkdFullCycleResult = {
  regime_label: string;
  agreement_code: string | null;
  import_duty_per_100: string | null;
  import_sales_tax_per_100: string;
  excise_per_100: string | null;
  finished_sst_per_100: string | null;
  import_total_per_100: string | null;
  full_cycle_total_per_100: string | null;
  import_effective_rate: string | null;
  simulated_full_cycle_rate: string | null;
  metric_name: string;
  is_statutory_rate: boolean;
};

export type CkdCalculationResult = {
  country_iso2: string;
  effective_date: string;
  powertrain: string;
  displacement_cc: number | null;
  origin_country_iso2: string;
  normalized_base: string;
  declaration_mode: string;
  miti_ckd_ap_confirmed: boolean;
  classification_note: string;
  hs_classification: {
    national_tariff_code: string;
    hs6_code: string;
    tariff_description: string;
    verification_status: VerificationStatus;
    source_code: string;
    source_locator: string;
  } | null;
  import_stage: {
    import_duty_options: CkdImportDutyOption[];
    import_sales_tax: ResolvedTreatment;
    import_effective_rates: Array<{
      regime_label: string; agreement_code: string | null; effective_rate: string | null;
    }>;
  };
  local_assembly_stage: {
    excise_duty: ResolvedTreatment;
    finished_vehicle_sales_tax: ResolvedTreatment;
    missing_for_complete_calculation: string[];
  };
  full_cycle_simulation: {
    available: boolean;
    message: string;
    required_inputs: Array<{ field: string; description: string; reason?: string }>;
    results: CkdFullCycleResult[] | null;
  };
  incentive_validation: IncentiveValidation | null;
  notes: string[];
  disclaimer: string;
};

export function calculateCkd(payload: {
  effective_date: string;
  origin_country_iso2: string;
  powertrain: string;
  displacement_cc?: number | null;
  body_type?: string;
  drive_type?: string;
  ckd_tariff_code?: string | null;
  customs_value?: string | null;
  declaration_mode?: string;
  miti_ckd_ap_confirmed?: boolean;
  selected_policy_codes?: string[];
  excise_value_ratio?: string | null;
  sales_value_ratio?: string | null;
}) {
  return writeRequest<CkdCalculationResult>("/ckd/calculate", "POST", payload);
}

export function getCcuTariffOptions(ccuCode: string, asOf: string) {
  const params = new URLSearchParams({ country: "MY", as_of: asOf });
  return request<{ total: number; items: CcuTariffOption[] }>(
    `/ccus/${encodeURIComponent(ccuCode)}/tariff-options?${params.toString()}`,
  );
}

export function getProjectBom(projectId: string) {
  return request<ProjectBomResponse>(`/projects/${projectId}/bom-lines`);
}

export function saveProjectBomLine(
  projectId: string,
  lineNo: number,
  payload: {
    enterprise_part_no: string;
    part_name: string | null;
    ccu_code: string;
    customs_value: string;
    quantity: string;
    currency_code: string;
    origin_country_iso2: string;
    local_or_imported: "IMPORTED" | "LOCAL";
    enterprise_inputs_complete: boolean;
    gri_2a_review_complete: boolean;
  },
) {
  return writeRequest<{ project_bom_line_id: string; bom: ProjectBomResponse }>(
    `/projects/${projectId}/bom-lines/${lineNo}`,
    "PUT",
    payload,
  );
}

export function saveProjectBomMapping(
  projectId: string,
  lineNo: number,
  regime: string,
  mappingCode: string,
) {
  return writeRequest<{ bom: ProjectBomResponse }>(
    `/projects/${projectId}/bom-lines/${lineNo}/tariff-selections/${regime}`,
    "PUT",
    {
      mapping_code: mappingCode,
      selected_by: "frontend-demo-user",
      selection_note: "项目BOM行显式选择",
    },
  );
}

export function previewProjectBomComparison(projectId: string) {
  return writeRequest<BomComparisonResult>(
    `/projects/${projectId}/bom-comparison/preview`,
    "POST",
    {
      requested_regimes: ["MFN", "ACFTA", "RCEP"],
      eligibility: {
        ACFTA: {
          proof_valid: false,
          origin_rule_compliance_confirmed: false,
          nomenclature_correlation_confirmed: true,
          enterprise_reviewed: false,
          simulation_only: true,
        },
        RCEP: {
          proof_valid: false,
          origin_rule_compliance_confirmed: false,
          nomenclature_correlation_confirmed: true,
          enterprise_reviewed: false,
          simulation_only: true,
        },
      },
      recoverable_sst_fraction: "0",
    },
  );
}

export function runProjectBomComparison(projectId: string) {
  return writeRequest<{
    result: BomComparisonResult;
    audit: {
      request_id: string;
      scenario_input_id: string;
      input_snapshot_id: string;
      runs: Array<{
        calculation_run_id: string;
        run_code: string;
        requested_regime: string;
        applied_regime: string;
        completeness: string;
      }>;
    };
  }>(`/projects/${projectId}/bom-comparison/run`, "POST", {
    requested_regimes: ["MFN", "ACFTA", "RCEP"],
    eligibility: {
      ACFTA: {
        proof_valid: false,
        origin_rule_compliance_confirmed: false,
        nomenclature_correlation_confirmed: true,
        enterprise_reviewed: false,
        simulation_only: true,
      },
      RCEP: {
        proof_valid: false,
        origin_rule_compliance_confirmed: false,
        nomenclature_correlation_confirmed: true,
        enterprise_reviewed: false,
        simulation_only: true,
      },
    },
    recoverable_sst_fraction: "0",
  });
}

export function previewProjectCalculation(projectId: string) {
  return writeRequest<ProjectCalculationPreview>(
    `/projects/${projectId}/calculations/preview`,
    "POST",
  );
}

export function runProjectCalculation(projectId: string) {
  return writeRequest<{
    calculation_run_id: string;
    run_code: string;
    preview: ProjectCalculationPreview;
  }>(`/projects/${projectId}/calculations/run`, "POST");
}

export function getCalculationRun(runId: string) {
  return request<CalculationRunDetail>(`/calculations/${runId}`);
}

export function getCalculationTrace(runId: string) {
  return request<{ run_id: string; items: DecisionTraceItem[] }>(
    `/calculations/${runId}/trace`,
  );
}

export function getCalculationMissingData(runId: string) {
  return request<{ run_id: string; items: CalculationMissingItem[] }>(
    `/calculations/${runId}/missing-data`,
  );
}

// ── Evidence / Policy Intelligence ─────────────────────────────────

export type EvidenceItem = {
  document_id: string;
  clause_id: string;
  document_title: string;
  authority_name: string;
  document_number: string | null;
  source_type: string;
  evidence_role: string;         // "TARIFF_RATE" | "TAX_FORMULA" | "ELIGIBILITY" | "ORIGIN_RULE" | "INCENTIVE" | "CLASSIFICATION"
  official_url: string | null;
  locator_type: string;
  locator_value: string;
  evidence_summary: string;
};

export type PolicyRule = {
  rule_code: string;
  rule_domain: string;
  rule_name_cn: string;
  rule_content: string;
  tariff_version: string;
  effective_from: string;
  effective_to: string | null;
  verification_status: VerificationStatus;
  verified_at: string | null;
  verified_by: string | null;
  clause_code: string;
  condition_summary: string[];
  condition_summary_status: string;
  formula_summary: string[];
  formula_summary_status: string;
  impact_scope: {
    vehicle_modes: string[] | null;
    powertrains: string[] | null;
    taxes: string[] | null;
  };
  evidence: EvidenceItem[];
};

export type PolicyRulesResponse = {
  country_iso2: string;
  as_of: string;
  total: number;
  page: number;
  page_size: number;
  items: PolicyRule[];
};

export function getCountryRules(
  iso2: string,
  params?: { domain?: string; status?: string; q?: string; page?: number; page_size?: number },
) {
  const qs = new URLSearchParams();
  if (params?.domain) qs.set("domain", params.domain);
  if (params?.status) qs.set("status", params.status);
  if (params?.q) qs.set("q", params.q);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString();
  return request<PolicyRulesResponse>(`/countries/${iso2}/rules${query ? `?${query}` : ""}`);
}

export function filterPolicyRules(
  rules: PolicyRule[],
  filters: { domain?: string; status?: string; q?: string },
): PolicyRule[] {
  let items = rules;
  if (filters.domain) {
    items = items.filter((r) => r.rule_domain === filters.domain);
  }
  if (filters.status) {
    items = items.filter((r) => r.verification_status === filters.status);
  }
  if (filters.q) {
    const q = filters.q.toLowerCase();
    items = items.filter((r) =>
      r.rule_name_cn.toLowerCase().includes(q) ||
      r.rule_code.toLowerCase().includes(q) ||
      r.rule_domain.toLowerCase().includes(q) ||
      r.rule_content?.toLowerCase().includes(q) ||
      r.evidence?.some((e) =>
        (e.document_title || "").toLowerCase().includes(q) ||
        (e.authority_name || "").toLowerCase().includes(q)
      )
    );
  }
  return items;
}

export function formatApiTime(value: string | null): string {
  if (!value) return "尚无核验时间";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatCount(value: number | undefined): string {
  return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

// ── Evidence ───────────────────────────────────────────────────────

export type SourceEvidenceDetail = {
  source_id: string;
  document_title: string;
  document_number: string | null;
  source_type: string;
  official_url: string | null;
  authority_name: string | null;
  locator: { locator_type: string; locator_value: string };
  original_excerpt: string | null;
  translated_excerpt_cn: string | null;
  effective_from: string | null;
  effective_to: string | null;
};

export function getSourceEvidence(sourceId: string) {
  return request<SourceEvidenceDetail>(`/sources/${encodeURIComponent(sourceId)}`);
}

export { API_BASE_URL };
