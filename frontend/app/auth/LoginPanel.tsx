"use client";

import {
  ArrowLeft,
  Building2,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  LogIn,
  ShieldCheck,
  Sparkles,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { useAuth } from "./AuthProvider";

type AuthMode = "login" | "register";

export function LoginPanel({ returnTo = "/" }: { returnTo?: string }) {
  const {
    authConfig,
    devLogin,
    oidcLoginUrl,
    personalLogin,
    registerPersonalAccount,
    status,
    error: authError,
    isAuthenticated,
    logout,
  } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);
  const [devBusy, setDevBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const safeReturnTo = useMemo(() => returnTo.startsWith("/") ? returnTo : "/", [returnTo]);
  // Older backends do not return this flag. Treating an omitted flag as
  // enabled keeps the standalone personal-account screen usable during the
  // rollout while an explicit false still respects the server configuration.
  const personalLoginEnabled = authConfig.personal_login_enabled !== false;

  if (isAuthenticated) {
    return (
      <main className="auth-page">
        <section className="auth-card" aria-labelledby="auth-title">
          <Link className="auth-back" href="/"><ArrowLeft size={16} /> 返回公开情报首页</Link>
          <div className="auth-mark"><LockKeyhole size={21} /></div>
          <span className="auth-kicker">AUTOPOLICY ACCESS</span>
          <h1 id="auth-title">当前账号暂不可访问此功能</h1>
          <p className="auth-lead">账号已经登录，但服务器尚未授予当前功能所需的权限。请返回首页，或退出后使用另一个账号登录。</p>
          <Link className="auth-primary" href="/"><ArrowLeft size={18} />返回首页</Link>
          <button type="button" className="auth-secondary" onClick={() => void logout()}><LogIn size={17} />退出并切换账号</button>
          <div className="auth-trust"><ShieldCheck size={16} /><span>权限由后端会话确认，前端不会通过隐藏按钮绕过访问控制。</span></div>
        </section>
      </main>
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const normalizedEmail = email.trim().toLowerCase();
    const normalizedName = displayName.trim();
    if (!normalizedEmail || !normalizedEmail.includes("@")) {
      setError("请输入有效的邮箱地址。");
      return;
    }
    if (password.length < 8) {
      setError("密码至少需要 8 个字符。");
      return;
    }
    if (mode === "register") {
      if (!normalizedName) {
        setError("请输入显示名。");
        return;
      }
      if (password !== confirmPassword) {
        setError("两次输入的密码不一致。");
        return;
      }
    }
    setBusy(true);
    try {
      if (mode === "register") {
        await registerPersonalAccount(normalizedEmail, password, normalizedName);
      } else {
        await personalLogin(normalizedEmail, password);
      }
      window.location.assign(safeReturnTo);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : mode === "register" ? "注册失败，请稍后重试。" : "登录失败，请检查邮箱和密码。");
    } finally {
      setBusy(false);
    }
  }

  async function handleDevLogin() {
    setDevBusy(true);
    setError(null);
    try {
      await devLogin();
      window.location.assign(safeReturnTo);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "开发登录失败");
    } finally {
      setDevBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-title">
        <Link className="auth-back" href="/"><ArrowLeft size={16} /> 返回公开情报首页</Link>
        <div className="auth-mark"><Sparkles size={21} /></div>
        <span className="auth-kicker">AUTOPOLICY ACCESS</span>
        <h1 id="auth-title">{mode === "login" ? "登录个人账号" : "创建个人账号"}</h1>
        <p className="auth-lead">使用个人账号访问 CBU、CKD、方案对比和 AI 助手。每个账号拥有独立的聊天记录和工作状态。</p>

        {(error || authError) && <div className="auth-error" role="alert">{error || authError}</div>}

        {personalLoginEnabled && (
          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            {mode === "register" && (
              <label className="auth-field">
                <span>显示名</span>
                <div className="auth-input-wrap"><UserRound size={16} /><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoComplete="name" placeholder="例如：张三" maxLength={200} disabled={busy} /></div>
              </label>
            )}
            <label className="auth-field">
              <span>邮箱</span>
              <div className="auth-input-wrap"><UserRound size={16} /><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" placeholder="name@example.com" maxLength={320} required disabled={busy} /></div>
            </label>
            <label className="auth-field">
              <span>密码</span>
              <div className="auth-input-wrap"><KeyRound size={16} /><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder="至少 8 个字符" minLength={8} required disabled={busy} /></div>
            </label>
            {mode === "register" && (
              <label className="auth-field">
                <span>确认密码</span>
                <div className="auth-input-wrap"><KeyRound size={16} /><input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" placeholder="再次输入密码" minLength={8} required disabled={busy} /></div>
              </label>
            )}
            <button type="submit" className="auth-primary auth-submit" disabled={busy || status === "loading"}>
              {busy ? <LoaderCircle className="spin" size={17} /> : <LogIn size={17} />}
              {busy ? (mode === "login" ? "正在登录…" : "正在创建账号…") : (mode === "login" ? "登录" : "注册并登录")}
            </button>
            <button type="button" className="auth-mode-toggle" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }} disabled={busy}>
              {mode === "login" ? "还没有账号？创建个人账号" : "已有账号？返回登录"}
            </button>
          </form>
        )}

        {(authConfig.oidc_enabled || authConfig.dev_login_enabled) && <div className="auth-alternatives"><span>其他登录方式</span></div>}
        {authConfig.oidc_enabled && (
          <a className="auth-secondary" href={oidcLoginUrl(safeReturnTo)}>
            <LogIn size={18} />
            使用{authConfig.oidc_provider_name || "企业单点登录"}
          </a>
        )}
        {authConfig.dev_login_enabled && (
          <button type="button" className="auth-secondary" disabled={devBusy || status === "loading"} onClick={() => void handleDevLogin()}>
            {devBusy ? <LoaderCircle className="spin" size={17} /> : <Building2 size={17} />}
            {devBusy ? "正在登录…" : (authConfig.dev_login_label || "使用本地开发账号")}
          </button>
        )}

        {!personalLoginEnabled && !authConfig.oidc_enabled && !authConfig.dev_login_enabled && (
          <div className="auth-unavailable"><LockKeyhole size={18} /><span>个人账号登录尚未启用，请联系系统管理员开启账号服务。</span></div>
        )}

        <div className="auth-trust"><ShieldCheck size={16} /><span>身份由后端会话确认；密码不会保存在浏览器中。</span></div>
      </section>
    </main>
  );
}
