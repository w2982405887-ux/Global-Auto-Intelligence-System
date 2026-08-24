"use client";

import { useSearchParams } from "next/navigation";
import { LoginPanel } from "../auth/LoginPanel";

export default function LoginPage() {
  const params = useSearchParams();
  const returnTo = params.get("return_to") || "/";
  return <LoginPanel returnTo={returnTo} />;
}

