"use client";

import {
  ApiError,
  API_BASE_URL,
  devLogin,
  getAuthConfig,
  getAuthMe,
  login as apiLogin,
  register as apiRegister,
  setCsrfToken,
  logout as apiLogout,
  switchOrganization as apiSwitchOrganization,
  type AuthConfig,
  type AuthMeResponse,
  type AuthUser,
  type Organization,
} from "../lib/api";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error";

export type AuthContextValue = {
  status: AuthStatus;
  isAuthenticated: boolean;
  user: AuthUser | null;
  organizations: Organization[];
  activeOrganization: Organization | null;
  permissions: string[];
  authConfig: AuthConfig;
  error: string | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
  personalLogin: (email: string, password: string) => Promise<void>;
  registerPersonalAccount: (email: string, password: string, displayName: string) => Promise<void>;
  devLogin: (email?: string) => Promise<void>;
  switchOrganization: (organizationId: string) => Promise<void>;
  hasPermission: (permission: string) => boolean;
  oidcLoginUrl: (returnTo?: string) => string;
};

const defaultAuthConfig: AuthConfig = {
  oidc_enabled: false,
  dev_login_enabled: false,
  personal_login_enabled: true,
};

const AuthContext = createContext<AuthContextValue | null>(null);

function normalizeAuthMe(value: AuthMeResponse | Record<string, unknown>): AuthMeResponse {
  const raw = value as Record<string, unknown>;
  const userRaw = (raw.user ?? raw.current_user ?? null) as Record<string, unknown> | null;
  const orgRaw = raw.active_organization ?? raw.current_organization ?? raw.organization ?? null;
  const organizationsRaw = raw.organizations ?? raw.memberships ?? [];
  const organizations = Array.isArray(organizationsRaw)
    ? organizationsRaw.map((item) => {
        const entry = (item ?? {}) as Record<string, unknown>;
        const organization = (entry.organization ?? entry.org ?? entry) as Record<string, unknown>;
        return {
          organization_id: String(
            organization.organization_id ?? organization.id ?? entry.organization_id ?? "",
          ),
          organization_code:
            (organization.organization_code ?? organization.code ?? entry.organization_code) as string | null | undefined,
          name: String(
            organization.name ?? organization.display_name ?? organization.organization_name ?? "未命名组织",
          ),
          display_name: (organization.display_name ?? organization.name) as string | null | undefined,
          role: (entry.role ?? entry.role_code ?? null) as string | null,
          membership_id: (entry.membership_id ?? entry.id ?? null) as string | null,
          status: String(organization.status ?? "ACTIVE"),
        };
      })
    : [];
  const activeObject = (orgRaw ?? null) as Record<string, unknown> | null;
  const activeId = activeObject
    ? String(activeObject.organization_id ?? activeObject.id ?? "")
    : "";
  const activeOrganization = activeId && activeObject
    ? organizations.find((item) => item.organization_id === activeId) ?? {
        organization_id: activeId,
        organization_code: (activeObject.organization_code ?? activeObject.code) as string | null | undefined,
        name: String(activeObject.name ?? activeObject.display_name ?? "当前组织"),
        display_name: (activeObject.display_name ?? activeObject.name) as string | null | undefined,
        role: (activeObject.role ?? null) as string | null,
        membership_id: (activeObject.membership_id ?? null) as string | null,
        status: String(activeObject.status ?? "ACTIVE"),
      }
    : organizations[0] ?? null;

  const authenticated = Boolean(
    raw.authenticated ?? raw.is_authenticated ?? userRaw?.user_id ?? userRaw?.id,
  );
  const user = userRaw
    ? {
        user_id: String(userRaw.user_id ?? userRaw.id ?? ""),
        email: (userRaw.email ?? null) as string | null,
        full_name: (userRaw.full_name ?? userRaw.name ?? null) as string | null,
        avatar_url: (userRaw.avatar_url ?? null) as string | null,
        status: (userRaw.status ?? "ACTIVE") as string,
      }
    : null;
  const permissionsRaw = raw.permissions ?? raw.effective_permissions ?? [];
  const permissions = Array.isArray(permissionsRaw)
    ? permissionsRaw.map((item) =>
        typeof item === "string"
          ? item
          : String((item as Record<string, unknown>)?.code ?? (item as Record<string, unknown>)?.permission ?? ""),
      ).filter(Boolean)
    : [];

  return {
    authenticated,
    user,
    organizations,
    active_organization: activeOrganization,
    permissions,
    csrf_token: typeof raw.csrf_token === "string" ? raw.csrf_token : undefined,
    auth_config: (raw.auth_config ?? raw.authentication ?? null) as Partial<AuthConfig> | null,
  };
}

function authErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) return "登录状态已失效，请重新登录。";
  if (error instanceof ApiError && error.status === 404) return "账号服务尚未启用，请联系系统管理员。";
  if (error instanceof Error) return error.message;
  return "无法读取当前账号状态。";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [session, setSession] = useState<AuthMeResponse>({
    authenticated: false,
    user: null,
    organizations: [],
    active_organization: null,
    permissions: [],
  });
  const [authConfig, setAuthConfig] = useState<AuthConfig>(defaultAuthConfig);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setStatus("loading");
    setError(null);
    const [meResult, configResult] = await Promise.allSettled([
      getAuthMe(),
      getAuthConfig(),
    ]);

    const configAvailable = configResult.status === "fulfilled";
    if (configAvailable) {
      setAuthConfig({ ...defaultAuthConfig, ...configResult.value });
    } else {
      // Do not expose a login link to an OIDC endpoint that the backend failed
      // to advertise or could not be reached.
      setAuthConfig(defaultAuthConfig);
    }

    if (meResult.status === "fulfilled") {
      const normalized = normalizeAuthMe(meResult.value);
      setSession(normalized);
      setCsrfToken(normalized.csrf_token);
      setStatus(normalized.authenticated ? "authenticated" : "unauthenticated");
      return;
    }

    const failure = meResult.reason;
    // A 401/404 is a normal anonymous state during rollout.  Public pages
    // remain usable while protected routes show the login guide.
    if (failure instanceof ApiError && (failure.status === 401 || failure.status === 404)) {
      setCsrfToken(null);
      setSession({ authenticated: false, user: null, organizations: [], active_organization: null, permissions: [] });
      setStatus("unauthenticated");
      return;
    }
    setStatus("error");
    setError(authErrorMessage(failure));
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    setError(null);
    try {
      await apiLogout();
    } finally {
      setCsrfToken(null);
      setSession({ authenticated: false, user: null, organizations: [], active_organization: null, permissions: [] });
      setStatus("unauthenticated");
    }
  }, []);

  const devLoginAction = useCallback(async (email?: string) => {
    if (!authConfig.dev_login_enabled) {
      throw new Error("开发登录未被后端启用。");
    }
    const result = await devLogin({ email });
    const normalized = normalizeAuthMe(result);
    setSession(normalized);
    setCsrfToken(normalized.csrf_token);
    setStatus(normalized.authenticated ? "authenticated" : "unauthenticated");
  }, [authConfig.dev_login_enabled]);

  const personalLogin = useCallback(async (email: string, password: string) => {
    setError(null);
    const result = await apiLogin({ email, password });
    const normalized = normalizeAuthMe(result);
    setSession(normalized);
    setCsrfToken(normalized.csrf_token);
    setStatus(normalized.authenticated ? "authenticated" : "unauthenticated");
  }, []);

  const registerPersonalAccount = useCallback(async (email: string, password: string, displayName: string) => {
    setError(null);
    const result = await apiRegister({ email, password, display_name: displayName });
    const normalized = normalizeAuthMe(result);
    setSession(normalized);
    setCsrfToken(normalized.csrf_token);
    setStatus(normalized.authenticated ? "authenticated" : "unauthenticated");
  }, []);

  const switchOrganization = useCallback(async (organizationId: string) => {
    setError(null);
    const result = await apiSwitchOrganization(organizationId);
    setSession((current) => ({
      ...current,
      active_organization:
        result.active_organization
          ?? current.organizations.find((item) => item.organization_id === result.organization_id)
          ?? current.organizations.find((item) => item.organization_id === organizationId)
          ?? current.active_organization,
    }));
  }, []);

  const hasPermission = useCallback((permission: string) => {
    if (session.permissions.includes("*")) return true;
    if (session.permissions.includes(permission)) return true;
    const [resource] = permission.split(".");
    return session.permissions.includes(`${resource}.*`);
  }, [session.permissions]);

  const oidcLoginUrl = useCallback((returnTo = "/") => {
    // API_BASE_URL is relative in the browser when the Vite same-origin
    // proxy is enabled.  Supplying the current origin keeps URL construction
    // valid for both relative local-dev and absolute deployed API URLs.
    const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;
    const url = new URL(`${API_BASE_URL}/auth/oidc/start`, origin);
    url.searchParams.set("return_to", returnTo);
    return url.toString();
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    status,
    isAuthenticated: status === "authenticated" && session.authenticated,
    user: session.user,
    organizations: session.organizations,
    activeOrganization: session.active_organization,
    permissions: session.permissions,
    authConfig,
    error,
    refresh,
    logout,
    personalLogin,
    registerPersonalAccount,
    devLogin: devLoginAction,
    switchOrganization,
    hasPermission,
    oidcLoginUrl,
  }), [authConfig, devLoginAction, error, hasPermission, logout, oidcLoginUrl, personalLogin, refresh, registerPersonalAccount, session, status, switchOrganization]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
