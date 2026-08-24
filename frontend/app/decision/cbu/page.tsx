"use client";

import { ArrowLeft, CarFront, Database, Globe2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const COUNTRIES = [
  {
    code: "MY",
    name: "马来西亚",
    href: "/decision/cbu/my",
    status: "完整 CBU 模板：日期、原产国、动力类型、车身/驱动、政策、税号、综合税率",
  },
  {
    code: "VN",
    name: "越南",
    href: "/decision/cbu/vn",
    status: "CBU 税链：越南税号、原产国/FTA、进口关税、SCT、VAT、特殊政策匹配",
  },
];

export default function CbuCountrySelectPage() {
  const [country, setCountry] = useState("MY");
  const selected = COUNTRIES.find((item) => item.code === country) ?? COUNTRIES[0];

  return (
    <main className="cbu-page">
      <div className="cbu-shell">
        <Link className="cbu-back" href="/">
          <ArrowLeft size={17} /> 返回全球决策
        </Link>

        <header className="cbu-hero">
          <div>
            <span className="cbu-eyebrow"><CarFront size={14} /> CBU VEHICLE IMPORT</span>
            <h1>CBU 整车进口税务分析</h1>
            <p>先选择目标国家。国家不同，税号体系、税种、FTA、优惠政策和计算顺序不同，系统会跳转到对应国家页面。</p>
          </div>
          <span className="cbu-db-state"><Database size={17} /> 实时连接政策数据库</span>
        </header>

        <section className="cbu-input-card">
          <div className="cbu-input-grid">
            <label className="cbu-full-width">
              <span><Globe2 size={15} /> 目标国家</span>
              <select value={country} onChange={(event) => setCountry(event.target.value)}>
                {COUNTRIES.map((item) => (
                  <option key={item.code} value={item.code}>{item.name} · {item.code}</option>
                ))}
              </select>
              <small>{selected.status}</small>
            </label>
          </div>

          <div className="cbu-empty-hint" style={{ marginTop: 24 }}>
            <CarFront size={40} />
            <h3>{selected.name} CBU 计算页面</h3>
            <p>{selected.status}</p>
            <Link className="cbu-calculate-btn" href={selected.href}>
              进入 {selected.name} CBU 工具
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
