"use client";

import { Check, ChevronDown, LoaderCircle, LogOut, UserRound, UsersRound } from "lucide-react";
import { useState } from "react";
import { useAuth } from "./AuthProvider";

function initials(name: string | null, email: string | null) {
  const value = (name || email || "用户").trim();
  const parts = value.split(/\s+/).filter(Boolean);
  if (parts.length > 1) return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  return value.slice(0, 2).toUpperCase();
}

export function UserMenu() {
  const { isAuthenticated, user, activeOrganization, organizations, switchOrganization, logout, authConfig, hasPermission } = useAuth();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canManageMembers = hasPermission("member.read") || hasPermission("member.manage") || hasPermission("role.manage");

  if (!isAuthenticated || !user) {
    return <a className="profile-button profile-login" href="/login" aria-label="登录">登录</a>;
  }

  async function handleOrganizationChange(organizationId: string) {
    if (!organizationId || organizationId === activeOrganization?.organization_id) return;
    setBusy(true);
    setError(null);
    try {
      await switchOrganization(organizationId);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "组织切换失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="user-menu">
      <button className="profile-button" type="button" aria-label="用户中心" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        {initials(user.full_name, user.email)} <ChevronDown size={13} />
      </button>
      {open && (
        <div className="user-menu-panel" role="menu">
          <div className="user-menu-heading"><UserRound size={16} /><span><strong>{user.full_name || "已登录用户"}</strong><small>{user.email || user.user_id}</small></span></div>
          <div className="user-menu-divider" />
          {organizations.length > 0 ? (
            <>
              <label className="org-switcher"><span>当前组织</span><select value={activeOrganization?.organization_id || ""} disabled={busy} onChange={(event) => void handleOrganizationChange(event.target.value)}>{organizations.map((organization) => <option key={organization.organization_id} value={organization.organization_id}>{organization.display_name || organization.name}</option>)}</select></label>
              {busy && <span className="user-menu-status"><LoaderCircle className="spin" size={13} />正在切换组织…</span>}
              {error && <span className="user-menu-error">{error}</span>}
              {activeOrganization && <div className="user-menu-org"><Check size={13} />{activeOrganization.display_name || activeOrganization.name}{activeOrganization.role ? ` · ${activeOrganization.role}` : ""}</div>}
            </>
          ) : (
            <div className="user-menu-personal"><UserRound size={14} />个人账号</div>
          )}
          <div className="user-menu-divider" />
          {canManageMembers && activeOrganization && <a className="user-menu-link" href="/settings/members" role="menuitem" onClick={() => setOpen(false)}><UsersRound size={14} />成员与权限</a>}
          {authConfig.oidc_provider_name && <small className="user-menu-auth">身份：{authConfig.oidc_provider_name}</small>}
          <button className="user-menu-logout" type="button" onClick={() => void logout()}><LogOut size={14} />退出登录</button>
        </div>
      )}
    </div>
  );
}
