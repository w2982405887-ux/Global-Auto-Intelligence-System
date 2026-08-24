"use client";

import {
  Activity,
  ArrowRight,
  ChevronDown,
  CircleAlert,
  Clock3,
  Factory,
  Globe2,
  Radar,
  Route,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { TradeGlobe } from "./components/TradeGlobe";
import { PolicyReviewDrawer, recentPolicyToReview } from "./components/PolicyReviewDrawer";
import { countries } from "./data/countries";
import { useAuth } from "./auth/AuthProvider";
import { UserMenu } from "./auth/UserMenu";
import {
  API_BASE_URL,
  type CountryOverview,
  type DashboardOverview,
  type TaxRoute,
  formatApiTime,
  formatCount,
  getCountryOverview,
  getCountryTaxRoutes,
  getDashboardOverview,
} from "./lib/api";

const statusClass = {
  已确认: "confirmed",
  待核验: "pending",
  趋势研判: "forecast",
} as const;

type PolicyFeedFilter = "ALL" | "CURRENT" | "FUTURE" | "EXPIRING" | "HIGH";

const policyStageLabel: Record<string, string> = {
  CURRENT: "已生效",
  FUTURE: "待生效",
  EXPIRING: "临近到期",
  EXPIRED_RECENT: "近期失效",
};

const policyCategoryLabel: Record<string, string> = {
  TAX: "税费",
  FTA_ORIGIN: "FTA / 原产地",
  ACCESS_APPROVAL: "准入 / 审批",
  INCENTIVE_LOCALIZATION: "优惠 / 本地化",
  CLASSIFICATION: "归类",
  STRATEGY: "产业趋势",
};

const impactScopeLabel: Record<string, string> = {
  CBU: "CBU",
  CKD: "CKD",
  BOTH: "CBU / CKD",
};

export default function Home() {
  const auth = useAuth();
  const [selectedCountryId, setSelectedCountryId] = useState<string | null>(
    null,
  );
  const [toolsOpen, setToolsOpen] = useState(false);
  const [dashboard, setDashboard] = useState<DashboardOverview | null>(null);
  const [policyFilter, setPolicyFilter] = useState<PolicyFeedFilter>("ALL");
  const [showAllPolicies, setShowAllPolicies] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState<DashboardOverview["recent_policies"][number] | null>(null);
  const [malaysiaOverview, setMalaysiaOverview] =
    useState<CountryOverview | null>(null);
  const [malaysiaRoutes, setMalaysiaRoutes] = useState<TaxRoute[]>([]);
  const [apiState, setApiState] = useState<
    "loading" | "connected" | "unavailable"
  >("loading");
  const [apiRetryToken, setApiRetryToken] = useState(0);

  const selectedCountry = useMemo(
    () =>
      countries.find((country) => country.id === selectedCountryId) ?? null,
    [selectedCountryId],
  );
  const selectedFromDatabase = selectedCountry?.code === "MY";

  useEffect(() => {
    const controller = new AbortController();
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    Promise.all([
      getDashboardOverview(controller.signal),
      getCountryOverview("MY", controller.signal),
      getCountryTaxRoutes("MY", controller.signal),
    ])
      .then(([dashboardData, countryData, routeData]) => {
        setDashboard(dashboardData);
        setMalaysiaOverview(countryData);
        setMalaysiaRoutes(routeData.items);
        setApiState("connected");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof DOMException && error.name === "AbortError") return;
        setApiState("unavailable");
        retryTimer = setTimeout(
          () => setApiRetryToken((current) => current + 1),
          5000,
        );
      });

    return () => {
      controller.abort();
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [apiRetryToken]);

  const selectedCompleteness =
    selectedFromDatabase && malaysiaOverview
      ? malaysiaOverview.completeness_percent
      : (selectedCountry?.completeness ?? 0);
  const selectedUpdateCount =
    selectedFromDatabase && malaysiaOverview
      ? malaysiaOverview.policy_nodes.statistics.current +
        malaysiaOverview.policy_nodes.statistics.future_effective
      : (selectedCountry?.updateCount ?? 0);

  const visiblePolicies = useMemo(() => {
    const policies = dashboard?.recent_policies ?? [];
    const filtered = policies.filter((policy) => {
      if (policyFilter === "HIGH") return policy.business_impact === "HIGH";
      if (policyFilter === "ALL") return true;
      return policy.policy_stage === policyFilter;
    });
    return showAllPolicies ? filtered : filtered.slice(0, 5);
  }, [dashboard?.recent_policies, policyFilter, showAllPolicies]);

  return (
    <main className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="topbar">
        <a className="brand" href="#" aria-label="汽车政策情报首页">
          <span className="brand-mark">
            <Globe2 size={20} />
          </span>
          <span>
            <strong>AutoPolicy</strong>
            <small>GLOBAL TRADE INTELLIGENCE</small>
          </span>
        </a>

        <nav className="main-nav" aria-label="主要导航">
          <a className="nav-link active" href="#">
            全球决策
          </a>
          <div className="nav-menu">
            <button
              className={`nav-link nav-button ${toolsOpen ? "open" : ""}`}
              type="button"
              aria-expanded={toolsOpen}
              onClick={() => setToolsOpen((current) => !current)}
            >
              决策工具
              <ChevronDown size={14} />
            </button>
            <AnimatePresence>
              {toolsOpen && (
                <motion.div
                  className="sub-menu"
                  initial={{ opacity: 0, y: -8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.98 }}
                  transition={{ duration: 0.18 }}
                >
                  <a href={auth.isAuthenticated && auth.hasPermission("calculation.run") ? "/decision/cbu" : "/login?return_to=%2Fdecision%2Fcbu"} className={!auth.isAuthenticated || !auth.hasPermission("calculation.run") ? "nav-item-gated" : undefined}>
                    <span className="menu-icon gold">
                      <Route size={17} />
                    </span>
                    <span>
                      <strong>CBU 整车进口计算</strong>
                      <small>整车进口税负测算</small>
                    </span>
                  </a>
                  <a href={auth.isAuthenticated && auth.hasPermission("calculation.run") ? "/decision/ckd" : "/login?return_to=%2Fdecision%2Fckd"} className={!auth.isAuthenticated || !auth.hasPermission("calculation.run") ? "nav-item-gated" : undefined}>
                    <span className="menu-icon mint">
                      <Factory size={17} />
                    </span>
                    <span>
                      <strong>CKD 散件进口计算</strong>
                      <small>整套CKD进口+本地组装</small>
                    </span>
                  </a>
                  <a href={auth.isAuthenticated && auth.hasPermission("calculation.run") ? "/decision/compare" : "/login?return_to=%2Fdecision%2Fcompare"} className={!auth.isAuthenticated || !auth.hasPermission("calculation.run") ? "nav-item-gated" : undefined}>
                    <span className="menu-icon blue">
                      <TrendingUp size={17} />
                    </span>
                    <span>
                      <strong>方案对比实验室</strong>
                      <small>CBU vs CKD 并排对比</small>
                    </span>
                  </a>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <a className="nav-link" href="/evidence">
            政策与证据
          </a>
          <a className="nav-link" href="#data">
            数据与审核
          </a>
        </nav>

        <div className="header-actions">
          <button className="icon-button" type="button" aria-label="搜索">
            <Search size={17} />
          </button>
          <a className="ai-button" href={auth.isAuthenticated && auth.hasPermission("assistant.chat") ? "/assistant" : "/login?return_to=%2Fassistant"}>
            <Sparkles size={15} />
            AI政策助手
          </a>
          <UserMenu />
        </div>
      </header>

      <section className="hero">
        <div className="globe-column">
          <div className="hero-copy">
            <motion.div
              className="eyebrow"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Radar size={14} />
              全球汽车进出口政策雷达
              <span>LIVE</span>
            </motion.div>
            <h1>
              从全球政策中，
              <br />
              找到更优的<span>出口路径</span>
            </h1>
            <p>
              点选重点国家，查看当前税制、未来节点与政策风险。所有结论最终都可追溯至规则、来源和计算过程。
            </p>
          </div>

          <TradeGlobe
            countries={countries}
            selectedCountry={selectedCountry}
            onSelect={(country) => setSelectedCountryId(country.id)}
          />

          <div className="globe-controls">
            <div className="live-indicator">
              <span />
              {apiState === "connected"
                ? "政策数据库已连接"
                : apiState === "loading"
                  ? "正在连接政策数据库"
                  : "政策数据库暂不可用"}
            </div>
            <div className="globe-hint">拖动探索 · 滚轮缩放 · 点选国家</div>
          </div>
        </div>

        <aside className="intel-column">
          <div className="intel-panel">
            <div className="panel-topline">
              <div>
                <span className="section-kicker">
                  <Activity size={13} />
                  INTELLIGENCE
                </span>
                <h2>{selectedCountry ? "国家情报" : "全球情报汇总"}</h2>
              </div>
              {selectedCountry && (
                <button
                  className="reset-button"
                  type="button"
                  onClick={() => setSelectedCountryId(null)}
                >
                  返回全球
                </button>
              )}
            </div>

            <AnimatePresence mode="wait">
              {selectedCountry ? (
                <motion.div
                  className="country-intel"
                  key={selectedCountry.id}
                  initial={{ opacity: 0, x: 24, filter: "blur(8px)" }}
                  animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
                  exit={{ opacity: 0, x: -16, filter: "blur(6px)" }}
                  transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
                >
                  <div className="country-heading">
                    <div className="country-code">{selectedCountry.code}</div>
                    <div>
                      <div className="country-title-row">
                        <h3>{selectedCountry.name}</h3>
                        <span
                          className={`policy-status ${statusClass[selectedCountry.status]}`}
                        >
                          {selectedCountry.status}
                        </span>
                      </div>
                      <p>
                        {selectedCountry.englishName} · {selectedCountry.region}
                      </p>
                      <span
                        className={`data-source-badge ${
                          selectedFromDatabase && apiState === "connected"
                            ? "live"
                            : "static"
                        }`}
                      >
                        {selectedFromDatabase && apiState === "connected"
                          ? "DATABASE LIVE"
                          : "尚未接入数据库"}
                      </span>
                    </div>
                  </div>

                  <div className="country-metrics">
                    <div>
                      <span>数据完整度</span>
                      <strong>{selectedCompleteness}%</strong>
                      <div className="progress-track">
                        <motion.span
                          initial={{ width: 0 }}
                          animate={{
                            width: `${selectedCompleteness}%`,
                          }}
                          transition={{ duration: 0.8, delay: 0.12 }}
                        />
                      </div>
                    </div>
                    <div>
                      <span>
                        {selectedFromDatabase ? "有效政策节点" : "待处理动态"}
                      </span>
                      <strong>{selectedUpdateCount}</strong>
                      <small>
                        {selectedFromDatabase ? "条数据库记录" : "条政策线索"}
                      </small>
                    </div>
                  </div>

                  <article className="headline-card">
                    <span>
                      {selectedFromDatabase ? "数据库状态" : "本期判断"}
                    </span>
                    <h4>
                      {selectedFromDatabase && malaysiaOverview
                        ? `五条税务路径已接入，${malaysiaOverview.route_readiness.filter((route) => route.route_verification_status === "VERIFIED").length}条达到VERIFIED`
                        : selectedCountry.headline}
                    </h4>
                    <p>
                      {selectedFromDatabase && malaysiaOverview
                        ? `核验时间：${formatApiTime(malaysiaOverview.last_verified_at)}`
                        : `最后更新于${selectedCountry.updatedAt}`}
                    </p>
                  </article>

                  <div className="policy-timeline">
                    <div className="timeline-item current">
                      <span className="timeline-dot" />
                      <div>
                        <small>当前有效</small>
                        <p>
                          {selectedFromDatabase && malaysiaOverview
                            ? `${formatCount(malaysiaOverview.policy_nodes.statistics.current)}个当前有效政策、审批或税率节点。`
                            : selectedCountry.currentPolicy}
                        </p>
                      </div>
                    </div>
                    <div className="timeline-item future">
                      <span className="timeline-dot" />
                      <div>
                        <small>未来节点</small>
                        <p>
                          {selectedFromDatabase && malaysiaOverview
                            ? `${formatCount(malaysiaOverview.policy_nodes.statistics.future_effective)}个已公布的未来生效节点，${formatCount(malaysiaOverview.policy_nodes.statistics.expiring)}个节点将在180天内到期。`
                            : selectedCountry.futurePolicy}
                        </p>
                      </div>
                    </div>
                    <div className="timeline-item risk">
                      <span className="timeline-dot" />
                      <div>
                        <small>关键风险</small>
                        <p>
                          {selectedFromDatabase && malaysiaOverview
                            ? `${formatCount(malaysiaOverview.open_missing_data)}项开放数据缺口；CANDIDATE税号不得直接用于正式计算。`
                            : selectedCountry.risk}
                        </p>
                      </div>
                    </div>
                  </div>

                  {selectedFromDatabase && malaysiaRoutes.length > 0 && (
                    <div className="route-readiness">
                      <div className="route-readiness-heading">
                        <span>五路径就绪度</span>
                        <small>来自 rules.vehicle_tax_route</small>
                      </div>
                      {malaysiaRoutes.map((route) => {
                        const readiness = malaysiaOverview?.route_readiness.find(
                          (item) => item.route_code === route.route_code,
                        );
                        return (
                          <div className="route-readiness-item" key={route.route_code}>
                            <span>{route.decision_order}</span>
                            <div>
                              <strong>{route.route_name_cn}</strong>
                              <small>
                                {formatCount(
                                  readiness?.tariff_line_count ||
                                    readiness?.ccu_tariff_mapping_count,
                                )}
                                条税率映射
                              </small>
                            </div>
                            <i
                              className={
                                route.verification_status === "VERIFIED"
                                  ? "verified"
                                  : "candidate"
                              }
                            >
                              {route.verification_status}
                            </i>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {selectedFromDatabase && malaysiaOverview && (malaysiaOverview.policy_nodes?.highlights?.length ?? 0) > 0 && (
                    <div className="policy-highlights">
                      <div className="policy-highlights-heading">
                        <span>官方依据</span>
                        <small>最近更新的政策节点及其来源</small>
                      </div>
                      {malaysiaOverview.policy_nodes.highlights.slice(0, 5).map((hl) => (
                        <div className="policy-highlight-item" key={hl.rule_code}>
                          <div className="policy-hl-info">
                            <strong>{hl.rule_name_cn}</strong>
                            <small>{hl.rule_domain || ""} · {hl.effective_from || ""}</small>
                          </div>
                          {hl.document_title && (
                            <a
                              className="policy-hl-source"
                              href={hl.official_url || "#"}
                              target="_blank"
                              rel="noopener noreferrer"
                              title={hl.document_title}
                            >
                              📄 {(hl.authority_name || "").slice(0, 18) || hl.document_title.slice(0, 20)}
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="panel-actions">
                    <button className="primary-action" type="button">
                      打开国家规则卡
                      <ArrowRight size={16} />
                    </button>
                    <a
                      className="secondary-action"
                      href={`/decision/new?country=${encodeURIComponent(selectedCountry.code)}&path=AUTO`}
                    >
                      开始方案测算
                    </a>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="global"
                  initial={{ opacity: 0, x: 18 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                  transition={{ duration: 0.34 }}
                >
                  <div className="summary-row">
                    <div className="summary-card">
                      <span className="summary-icon mint">
                        <Globe2 size={16} />
                      </span>
                      <strong>
                        {apiState === "connected"
                          ? formatCount(dashboard?.connected_country_count)
                          : "—"}
                      </strong>
                      <small>已接入国家</small>
                    </div>
                    <div className="summary-card">
                      <span className="summary-icon gold">
                        <Clock3 size={16} />
                      </span>
                      <strong>
                        {apiState === "connected"
                          ? formatCount(dashboard?.active_special_policy_count)
                          : "—"}
                      </strong>
                      <small>当前有效特殊优惠</small>
                    </div>
                    <div className="summary-card">
                      <span className="summary-icon coral">
                        <CircleAlert size={16} />
                      </span>
                      <strong>
                        {apiState === "connected"
                          ? formatCount(dashboard?.pending_review_policy_count)
                          : "—"}
                      </strong>
                      <small>待人工核验</small>
                    </div>
                  </div>

                  <div className="feed-heading">
                    <div>
                      <h3>最新政策动态</h3>
                      <small>
                        数据截至 {dashboard?.as_of ?? "当前日期"} · 特殊优惠政策 {formatCount(dashboard?.special_policy_count)} 条 · 按生效阶段和业务影响排序
                      </small>
                    </div>
                    <button
                      type="button"
                      onClick={() => setShowAllPolicies((current) => !current)}
                    >
                      {showAllPolicies ? "收起" : "查看全部"}
                    </button>
                  </div>

                  <div className="policy-filter-row" role="tablist" aria-label="政策动态筛选">
                    {(
                      [
                        ["ALL", "全部"],
                        ["CURRENT", "已生效"],
                        ["FUTURE", "待生效"],
                        ["EXPIRING", "临近到期"],
                        ["HIGH", "高影响"],
                      ] as const
                    ).map(([value, label]) => (
                      <button
                        className={policyFilter === value ? "active" : ""}
                        key={value}
                        type="button"
                        role="tab"
                        aria-selected={policyFilter === value}
                        onClick={() => {
                          setPolicyFilter(value);
                          setShowAllPolicies(false);
                        }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  <div className="intel-feed">
                    {visiblePolicies.map((update, index) => (
                      <motion.button
                        className="feed-item"
                        type="button"
                        key={update.rule_code}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.06 * index }}
                        onClick={() => setSelectedPolicy(update)}
                      >
                        <span className="feed-badges">
                          <span
                            className={`feed-level level-${
                              update.policy_stage === "FUTURE"
                                ? "节点"
                                : update.policy_stage === "EXPIRING"
                                  ? "变化"
                                  : update.business_impact === "HIGH"
                                    ? "重点"
                                    : "缺口"
                            }`}
                          >
                            {policyStageLabel[update.policy_stage ?? ""] ??
                              (update.verification_status === "VERIFIED" ? "已核验" : "待核验")}
                          </span>
                          <span className="feed-category">
                            {policyCategoryLabel[update.policy_category ?? ""] ?? "政策"}
                          </span>
                        </span>
                        <span className="feed-copy">
                          <small>
                            {update.country_name_cn} · {impactScopeLabel[update.impact_scope ?? "BOTH"] ?? "CBU / CKD"} · {update.rule_code}
                          </small>
                          <strong>{update.rule_name_cn}</strong>
                          <em>
                            {update.freshness_status === "STALE"
                              ? "需重新核验"
                              : update.freshness_status === "UNVERIFIED"
                                ? "待官方核验"
                                : update.last_verified_at
                                  ? `来源核验于 ${formatApiTime(update.last_verified_at)}`
                                  : "来源核验时间待补充"}
                          </em>
                        </span>
                        {(update.canonical_url || update.document_title) && (
                          <a
                            className="feed-source-dot"
                            href={update.canonical_url || "#"}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            title={update.document_title || "查看政策原文"}
                          >
                            📄
                          </a>
                        )}
                        <ArrowRight size={15} />
                      </motion.button>
                    ))}
                    {apiState === "connected" && visiblePolicies.length === 0 && (
                      <div className="feed-state">当前筛选条件下暂无政策动态。</div>
                    )}
                    {apiState === "loading" && (
                      <div className="feed-state">正在读取政策与证据视图…</div>
                    )}
                    {apiState === "unavailable" && (
                      <div className="feed-state error">
                        <span>
                          暂时无法连接 {API_BASE_URL}
                          ，系统将在5秒后自动重试。
                        </span>
                        <button
                          type="button"
                          className="feed-retry-button"
                          onClick={() => {
                            setApiState("loading");
                            setApiRetryToken((current) => current + 1);
                          }}
                        >
                          立即重试
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="confidence-note">
                    <ShieldCheck size={18} />
                    <div>
                      <strong>结论可信度由数据完整度控制</strong>
                      <p>
                        缺少决定性数据时，系统只输出部分税负或结果区间，不生成虚假的综合税率。
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </aside>
      </section>

      <section className="country-dock" aria-label="重点国家快捷选择">
        <div className="dock-label">
          <span />
          重点市场
        </div>
        <div className="country-list">
          {countries.map((country) => (
            <button
              type="button"
              key={country.id}
              className={selectedCountryId === country.id ? "selected" : ""}
              onClick={() => setSelectedCountryId(country.id)}
              aria-pressed={selectedCountryId === country.id}
            >
              <span>{country.code}</span>
              {country.name}
              {country.updateCount >= 6 && <i>{country.updateCount}</i>}
            </button>
          ))}
        </div>
      </section>

      <PolicyReviewDrawer
        policy={selectedPolicy ? recentPolicyToReview(selectedPolicy) : null}
        onClose={() => setSelectedPolicy(null)}
      />

    </main>
  );
}
