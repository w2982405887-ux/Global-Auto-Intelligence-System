import type { Metadata } from "next";
import { headers } from "next/headers";
import { AuthProvider } from "./auth/AuthProvider";
import { AuthRouteBoundary } from "./auth/AuthRouteBoundary";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "localhost:3000";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ??
    (host.startsWith("localhost") ? "http" : "https");
  const baseUrl = `${protocol}://${host}`;
  const title = "AutoPolicy · 全球汽车贸易政策情报";
  const description =
    "面向汽车进出口决策的全球政策情报、KD归类和综合税率测算工作台。";

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      images: [
        {
          url: `${baseUrl}/og.png`,
          width: 1736,
          height: 904,
          alt: "AutoPolicy全球汽车贸易政策情报",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [`${baseUrl}/og.png`],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <AuthProvider>
          <AuthRouteBoundary>{children}</AuthRouteBoundary>
        </AuthProvider>
      </body>
    </html>
  );
}
