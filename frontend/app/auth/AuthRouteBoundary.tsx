"use client";

import { LoaderCircle } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import { useAuth } from "./AuthProvider";
import { LoginPanel } from "./LoginPanel";

function isProtectedPath(pathname: string) {
  return pathname === "/assistant" || pathname.startsWith("/assistant/") || pathname === "/decision" || pathname.startsWith("/decision/") || pathname === "/settings/members";
}

export function AuthRouteBoundary({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { status, isAuthenticated, hasPermission } = useAuth();

  if (!isProtectedPath(pathname)) return <>{children}</>;
  if (status === "loading") {
    return <main className="auth-loading"><LoaderCircle className="spin" size={24} /><span>正在确认账号与组织权限…</span></main>;
  }
  const requiredPermission = pathname === "/assistant" || pathname.startsWith("/assistant/")
    ? "assistant.chat"
    : pathname === "/settings/members"
      ? "member.read"
      : "calculation.run";
  if (status !== "authenticated" || !isAuthenticated || !hasPermission(requiredPermission)) {
    const query = searchParams.toString();
    const returnTo = `${pathname}${query ? `?${query}` : ""}`;
    return <LoginPanel returnTo={returnTo} />;
  }
  return <>{children}</>;
}
