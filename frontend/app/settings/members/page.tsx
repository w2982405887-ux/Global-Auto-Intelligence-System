"use client";

import {
  ArrowLeft,
  Check,
  LoaderCircle,
  MailPlus,
  RefreshCw,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ApiError,
  getOrganizationMembers,
  inviteOrganizationMember,
  updateOrganizationMember,
  type OrganizationMember,
} from "../../lib/api";
import { useAuth } from "../../auth/AuthProvider";

const ROLE_OPTIONS = [
  { value: "viewer", label: "只读用户" },
  { value: "analyst", label: "分析员" },
  { value: "project_manager", label: "项目经理" },
  { value: "policy_editor", label: "政策编辑员" },
  { value: "policy_reviewer", label: "政策审核员" },
  { value: "org_admin", label: "组织管理员" },
  { value: "audit_reader", label: "审计只读" },
];

const roleLabel = new Map(ROLE_OPTIONS.map((item) => [item.value, item.label]));

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(date);
}

function memberName(member: OrganizationMember) {
  return member.display_name?.trim() || member.email || member.user_id;
}

export default function MembersPage() {
  const {
    activeOrganization,
    hasPermission,
    isAuthenticated,
  } = useAuth();
  const canInvite = hasPermission("member.manage");
  const canEditRoles = hasPermission("role.manage");
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [rowBusy, setRowBusy] = useState<string | null>(null);
  const [rowDrafts, setRowDrafts] = useState<Record<string, { role: string; status: "ACTIVE" | "SUSPENDED" }>>({});
  const [invite, setInvite] = useState({ email: "", role_code: "viewer", expires_in_days: 7 });
  const [inviteBusy, setInviteBusy] = useState(false);
  const [invitationToken, setInvitationToken] = useState<string | null>(null);

  const organizationId = activeOrganization?.organization_id ?? null;

  async function loadMembers(options?: { quiet?: boolean }) {
    if (!organizationId) {
      setMembers([]);
      setLoading(false);
      return;
    }
    if (options?.quiet) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const result = await getOrganizationMembers(organizationId);
      setMembers(result.items);
      setRowDrafts(Object.fromEntries(result.items.map((member) => [
        member.membership_id,
        { role: member.role_codes[0] || "viewer", status: member.status === "SUSPENDED" ? "SUSPENDED" : "ACTIVE" },
      ])));
    } catch (cause) {
      const message = cause instanceof ApiError && cause.status === 403
        ? "当前账号没有读取组织成员的权限。"
        : cause instanceof Error ? cause.message : "组织成员读取失败。";
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    void loadMembers();
    // The active organization is the explicit data boundary for this page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId]);

  const activeCount = useMemo(() => members.filter((member) => member.status === "ACTIVE").length, [members]);

  async function createInvitation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!organizationId || !invite.email.trim() || inviteBusy) return;
    setInviteBusy(true);
    setError(null);
    setNotice(null);
    setInvitationToken(null);
    try {
      const result = await inviteOrganizationMember(organizationId, {
        email: invite.email.trim(),
        role_code: invite.role_code,
        expires_in_days: invite.expires_in_days,
      });
      setInvitationToken(result.invitation_token);
      setNotice(`邀请已创建：${result.invitation.email}，有效期至 ${formatDate(result.invitation.expires_at)}。`);
      setInvite((current) => ({ ...current, email: "" }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "邀请创建失败。请检查邮箱和权限。");
    } finally {
      setInviteBusy(false);
    }
  }

  async function saveMember(member: OrganizationMember) {
    if (!organizationId || !canEditRoles || rowBusy) return;
    const draft = rowDrafts[member.membership_id];
    if (!draft) return;
    setRowBusy(member.membership_id);
    setError(null);
    setNotice(null);
    try {
      await updateOrganizationMember(organizationId, member.membership_id, {
        role_codes: [draft.role],
        status: draft.status,
      });
      setNotice(`已更新 ${memberName(member)} 的角色与状态。`);
      await loadMembers({ quiet: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "成员权限更新失败。");
    } finally {
      setRowBusy(null);
    }
  }

  if (!isAuthenticated) return null;

  return (
    <main className="members-page">
      <div className="members-shell">
        <Link className="members-back" href="/"><ArrowLeft size={17} /> 返回全球决策</Link>
        <header className="members-hero">
          <div>
            <span className="members-eyebrow"><UsersRound size={14} /> ORGANIZATION ACCESS</span>
            <h1>成员与权限</h1>
            <p>管理当前组织的成员、角色和访问状态。最终权限以服务器端 RBAC 校验为准。</p>
          </div>
          <div className="members-org-pill"><ShieldCheck size={16} /><span>{activeOrganization?.display_name || activeOrganization?.name || "未选择组织"}</span></div>
        </header>

        {!organizationId && <div className="members-empty"><ShieldCheck size={22} /><span>当前账号还没有可用的组织上下文，请先从右上角切换组织。</span></div>}
        {error && <div className="members-alert error" role="alert">{error}</div>}
        {notice && <div className="members-alert success" role="status"><Check size={16} />{notice}</div>}

        {organizationId && (
          <>
            <section className="members-summary">
              <div><span>组织成员</span><strong>{members.length}</strong><small>已建立成员关系</small></div>
              <div><span>当前有效</span><strong>{activeCount}</strong><small>可访问组织工作区</small></div>
              <button type="button" className="members-refresh" disabled={loading || refreshing} onClick={() => void loadMembers({ quiet: true })}>{refreshing ? <LoaderCircle className="spin" size={16} /> : <RefreshCw size={16} />}刷新</button>
            </section>

            {canInvite && (
              <section className="members-card">
                <div className="members-card-heading"><div><span className="members-section-kicker">INVITATION</span><h2>邀请新成员</h2></div><MailPlus size={20} /></div>
                <form className="invite-form" onSubmit={(event) => void createInvitation(event)}>
                  <label><span>邮箱</span><input type="email" required value={invite.email} onChange={(event) => setInvite((current) => ({ ...current, email: event.target.value }))} placeholder="name@company.com" /></label>
                  <label><span>初始角色</span><select value={invite.role_code} onChange={(event) => setInvite((current) => ({ ...current, role_code: event.target.value }))}>{ROLE_OPTIONS.map((role) => <option value={role.value} key={role.value}>{role.label}</option>)}</select></label>
                  <label><span>有效期</span><select value={invite.expires_in_days} onChange={(event) => setInvite((current) => ({ ...current, expires_in_days: Number(event.target.value) }))}><option value={7}>7 天</option><option value={14}>14 天</option><option value={30}>30 天</option></select></label>
                  <button type="submit" className="members-primary" disabled={inviteBusy || !invite.email.trim()}>{inviteBusy ? <LoaderCircle className="spin" size={16} /> : <MailPlus size={16} />}创建邀请</button>
                </form>
                {invitationToken && <div className="invitation-token"><strong>一次性邀请令牌</strong><code>{invitationToken}</code><small>令牌只在本次响应中展示，请交给受邀成员或后续邮件服务。</small></div>}
              </section>
            )}

            <section className="members-card">
              <div className="members-card-heading"><div><span className="members-section-kicker">MEMBERS</span><h2>当前组织成员</h2></div><span className="members-permission-note">{canEditRoles ? "可编辑角色与状态" : "只读"}</span></div>
              {loading ? <div className="members-loading"><LoaderCircle className="spin" size={20} />正在读取成员…</div> : members.length === 0 ? <div className="members-empty"><UsersRound size={22} /><span>当前组织暂无成员记录。</span></div> : (
                <div className="members-table-wrap">
                  <table className="members-table">
                    <thead><tr><th>成员</th><th>角色</th><th>状态</th><th>加入信息</th>{canEditRoles && <th>操作</th>}</tr></thead>
                    <tbody>{members.map((member) => {
                      const draft = rowDrafts[member.membership_id] || { role: member.role_codes[0] || "viewer", status: member.status === "SUSPENDED" ? "SUSPENDED" : "ACTIVE" };
                      return <tr key={member.membership_id}>
                        <td><strong>{memberName(member)}</strong><small>{member.email || member.user_id}</small></td>
                        <td>{canEditRoles ? <select value={draft.role} onChange={(event) => setRowDrafts((current) => ({ ...current, [member.membership_id]: { ...draft, role: event.target.value } }))}>{ROLE_OPTIONS.map((role) => <option value={role.value} key={role.value}>{role.label}</option>)}</select> : <span className="role-list">{member.role_codes.map((role) => roleLabel.get(role) || role).join("、") || "未分配"}</span>}</td>
                        <td>{canEditRoles ? <select value={draft.status} onChange={(event) => setRowDrafts((current) => ({ ...current, [member.membership_id]: { ...draft, status: event.target.value as "ACTIVE" | "SUSPENDED" } }))}><option value="ACTIVE">有效</option><option value="SUSPENDED">已暂停</option></select> : <span className={`member-status ${member.status === "ACTIVE" ? "active" : "suspended"}`}>{member.status === "ACTIVE" ? "有效" : "已暂停"}</span>}</td>
                        <td><small>成员 ID</small><code>{member.membership_id.slice(0, 8)}…</code></td>
                        {canEditRoles && <td><button type="button" className="member-save" disabled={rowBusy === member.membership_id} onClick={() => void saveMember(member)}>{rowBusy === member.membership_id ? <LoaderCircle className="spin" size={14} /> : "保存"}</button></td>}
                      </tr>;
                    })}</tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
