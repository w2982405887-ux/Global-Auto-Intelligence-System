export type ScenarioRate = {
  regime: string;
  rate: string | null;
  scope: "FULL_CHAIN" | "IMPORT_STAGE" | "PARTIAL_CHAIN";
  complete: boolean;
};

export type ScenarioSnapshot = {
  countryIso2: "MY" | "VN";
  countryName: string;
  route: "CBU" | "CKD";
  title: string;
  effectiveDate: string;
  originCountryIso2: string;
  powertrain: string;
  status: "COMPLETE" | "PARTIAL" | "BLOCKED";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  scopeLabel: string;
  tariffCodes: string[];
  rates: ScenarioRate[];
  missingItems: string[];
  notes: string[];
};

export type ScenarioWorkspaceProps = {
  embedded?: boolean;
  onSnapshot?: (snapshot: ScenarioSnapshot | null) => void;
};

export function decimalRate(value: string | null | undefined) {
  if (value == null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
