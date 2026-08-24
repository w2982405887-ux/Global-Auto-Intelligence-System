"use client";

import { ArrowLeft, Database, Factory, Globe2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

const COUNTRIES = [
  {
    code: "MY",
    name: "马来西亚",
    href: "/decision/ckd/my",
    status: "完整 CKD 模板：整套税号、进口环节、本地组装阶段、估值系数模拟",
  },
  {
    code: "VN",
    name: "越南",
    href: "/decision/ckd/vn",
    status: "越南 CKD 第一阶段：按动力类型估算主要部件进口关税，暂不计算本地组装后 SCT/VAT",
  },
];

export default function CkdCountrySelectPage() {
  const [country, setCountry] = useState("VN");
  const selected = COUNTRIES.find((item) => item.code === country) ?? COUNTRIES[0];

  return (
    <main className="ckd-page">
      <div className="ckd-shell">
        <Link className="ckd-back" href="/"><ArrowLeft size={17} /> 返回全球决策</Link>
        <header className="ckd-hero">
          <div>
            <span className="ckd-eyebrow"><Factory size={14} /> CKD / KD IMPORT</span>
            <h1>CKD 散件进口与本地组装税务分析</h1>
            <p>先选择目标国家。国家不同，CKD归类方式、零件税号、FTA、进口税费和本地组装税费计算逻辑不同。</p>
          </div>
          <span className="ckd-db-state"><Database size={17} /> 实时连接政策数据库</span>
        </header>

        <section className="ckd-input-card">
          <div className="ckd-input-grid">
            <label className="ckd-full-width">
              <span><Globe2 size={15} /> 目标国家</span>
              <select value={country} onChange={(event) => setCountry(event.target.value)}>
                {COUNTRIES.map((item) => <option key={item.code} value={item.code}>{item.name} · {item.code}</option>)}
              </select>
              <small>{selected.status}</small>
            </label>
          </div>
          <div className="ckd-empty-hint" style={{ marginTop: 24 }}>
            <Factory size={40} />
            <h3>{selected.name} CKD 计算页面</h3>
            <p>{selected.status}</p>
            <Link className="ckd-calculate-btn" href={selected.href}>进入 {selected.name} CKD 工具</Link>
          </div>
        </section>
      </div>
    </main>
  );
}
