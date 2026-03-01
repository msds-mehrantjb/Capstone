import React, { useEffect, useMemo, useState } from "react";
import {
  ShieldCheck,
  ChevronDown,
  Plus,
  CheckCircle2,
  BadgeCheck,
  AlertTriangle,
  FileText,
} from "lucide-react";

type StepStatus = "Blocked" | "Not Started" | "In Progress" | "Completed";

type DashboardDTO = {
  environment: string;
  scope: { name: string; asset_count: number; status: StepStatus };
  kpis: {
    readiness_score: { value: number; max: number; label: string; delta_7d: number };
    evidence_coverage: { percent: number; have: number; total: number };
    open_high_critical: { count: number; unresolved: number };
    soa: { status: StepStatus; label: string; pending_approvals: number };
  };
  blockers: {
    id: string;
    severity: "info" | "medium" | "high" | "critical";
    title: string;
    iso_ref?: string;
    assets: string[];
    cta: string;
  }[];
};

type SystemStatusDTO = {
  meta: { name: string; version: string };
  sections: Record<string, { status: StepStatus }>;
};

type ScopeDocDTO = {
  meta?: Record<string, any>;
  sections?: Array<{
    id?: string;
    title?: string;
    body?: string;
    bullets?: string[];
  }>;
};

const NAV_STEPS = [
  { step: 1, name: "Scope & Context" },
  { step: 2, name: "Asset Inventory & CIA" },
  { step: 3, name: "Threats & Vulnerabilities" },
  { step: 4, name: "Existing Controls & Posture" },
  { step: 5, name: "Risk Analysis" },
  { step: 6, name: "Risk Evaluation" },
  { step: 7, name: "Risk Treatment" },
  { step: 8, name: "Annex A & SoA" },
  { step: 9, name: "Action Plan / Implementation" },
  { step: 10, name: "Monitoring & Improvement" },
  { step: 11, name: "Final Deliverables" },
] as const;

const STEP_TO_SECTION_KEY: Record<number, string> = {
  1: "scope_context",
  2: "assets_cia",
  3: "threats_vulns",
  4: "controls_posture",
  5: "risk_analysis",
  6: "risk_evaluation",
  7: "risk_treatment",
  8: "soa",
  9: "action_plan",
  10: "monitoring",
  11: "reports",
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function apiGetJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as T;
}

async function apiGetSystemStatus(): Promise<SystemStatusDTO> {
  return apiGetJSON<SystemStatusDTO>(`/api/system/status`);
}

async function apiGetLatestScope(year: number): Promise<ScopeDocDTO> {
  return apiGetJSON<ScopeDocDTO>(`/api/scope/latest?year=${encodeURIComponent(String(year))}`);
}

/** --- UI helpers --- */

function StatusDot({ status }: { status: StepStatus }) {
  const cls =
    status === "Completed"
      ? "bg-emerald-400"
      : status === "In Progress"
        ? "bg-orange-400"
        : status === "Not Started"
          ? "bg-yellow-400"
          : "bg-rose-400";
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${cls}`} />;
}

function Pill({
  tone,
  children,
}: {
  tone: "emerald" | "sky" | "amber" | "rose" | "slate";
  children: React.ReactNode;
}) {
  const map: Record<typeof tone, string> = {
    emerald: "bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-500/25",
    sky: "bg-yellow-500/15 text-yellow-200 ring-1 ring-yellow-500/25", // Not Started
    amber: "bg-orange-500/15 text-orange-200 ring-1 ring-orange-500/25", // In Progress
    rose: "bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/25", // Blocked
    slate: "bg-white/5 text-slate-200 ring-1 ring-white/10",
  };
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs ${map[tone]}`}>
      {children}
    </span>
  );
}

function Card({
  children,
  accent,
}: {
  children: React.ReactNode;
  accent: "amber" | "emerald" | "rose" | "slate";
}) {
  const ring =
    accent === "amber"
      ? "ring-amber-500/25"
      : accent === "emerald"
        ? "ring-emerald-500/25"
        : accent === "rose"
          ? "ring-rose-500/25"
          : "ring-white/10";
  return (
    <div className={`relative overflow-hidden rounded-2xl bg-white/5 p-5 shadow-xl ring-1 ${ring} border border-white/10`}>
      <div className="pointer-events-none absolute inset-0 opacity-60 [background:radial-gradient(80%_60%_at_10%_0%,rgba(255,255,255,0.10),transparent_60%)]" />
      <div className="relative">{children}</div>
    </div>
  );
}

function MiniBar({
  valuePct,
  tone,
}: {
  valuePct: number;
  tone: "amber" | "emerald" | "rose" | "slate";
}) {
  const fill =
    tone === "amber"
      ? "bg-amber-400"
      : tone === "emerald"
        ? "bg-emerald-400"
        : tone === "rose"
          ? "bg-rose-400"
          : "bg-slate-200";
  return (
    <div className="mt-3 h-2 w-full rounded-full bg-white/10">
      <div className={`h-2 rounded-full ${fill}`} style={{ width: `${Math.max(0, Math.min(100, valuePct))}%` }} />
    </div>
  );
}

const labelTone = (s: StepStatus) => {
  if (s === "Completed") return "emerald";
  if (s === "In Progress") return "amber";
  if (s === "Not Started") return "sky";
  return "rose";
};

export default function Dashboard() {
  const [env, setEnv] = useState("Production");
  const [data, setData] = useState<DashboardDTO | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatusDTO | null>(null);
  const [scopeDoc, setScopeDoc] = useState<ScopeDocDTO | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [selectedStep, setSelectedStep] = useState<number>(3);

  useEffect(() => {
    (async () => {
      try {
        setErr(null);

        const [json, sys] = await Promise.all([
          apiGetJSON<DashboardDTO>(`/api/dashboard/summary?env=${encodeURIComponent(env)}`),
          apiGetSystemStatus(),
        ]);

        setData(json);
        setSystemStatus(sys);
      } catch (e) {
        setErr(e instanceof Error ? e.message : String(e));
        setData(null);
        setSystemStatus(null);
      }
    })();
  }, [env]);

  const scopeSectionStatus: StepStatus =
    systemStatus?.sections?.scope_context?.status ?? "Blocked";

  const isScopeUnavailable =
    scopeSectionStatus === "Blocked" || scopeSectionStatus === "Not Started";

  // Fetch latest Scope doc only when needed (In Progress / Completed)
  useEffect(() => {
    (async () => {
      try {
        if (isScopeUnavailable) {
          setScopeDoc(null);
          return;
        }
        const doc = await apiGetLatestScope(2026);
        setScopeDoc(doc);
      } catch (e) {
        // don’t kill the whole dashboard—just drop the scope details
        setScopeDoc(null);
      }
    })();
  }, [isScopeUnavailable]);

  const displayScopeName = isScopeUnavailable ? "NA" : (data?.scope?.name ?? "NA");
  const displayAssetCount = isScopeUnavailable ? 0 : (data?.scope?.asset_count ?? 0);

  const section2Items = useMemo(() => {
    if (isScopeUnavailable) return [];
    const secs = scopeDoc?.sections ?? [];
    const sec2 =
      secs.find((s) => (s.id || "").trim() === "org_boundaries") ||
      secs.find((s) => ((s.title || "").trim().startsWith("2.")));
    const bullets = Array.isArray(sec2?.bullets) ? sec2!.bullets! : [];
    return bullets.map((b) => (typeof b === "string" ? b.trim() : "")).filter(Boolean);
  }, [scopeDoc, isScopeUnavailable]);

  const lifecycle = useMemo(() => {
    return NAV_STEPS.map((s) => {
      const key = STEP_TO_SECTION_KEY[s.step];
      const status = systemStatus?.sections?.[key]?.status ?? "Blocked";
      return { ...s, status };
    });
  }, [systemStatus]);

  return (
    <div className="min-h-screen bg-[#070A12] text-slate-50">
      <div className="flex min-h-screen">
        {/* Sidebar */}
        <aside className="w-[280px] border-r border-white/10 bg-[#060815]">
          <div className="px-6 py-6">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-sky-500/15 ring-1 ring-sky-500/25">
                <ShieldCheck className="h-5 w-5 text-sky-200" />
              </div>
              <div>
                <div className="text-lg font-semibold tracking-tight">ISO 27001</div>
                <div className="text-sm text-slate-400">Audit Lifecycle</div>
              </div>
            </div>
          </div>

          <nav className="px-3">
            {NAV_STEPS.map((item) => {
              const active = selectedStep === item.step;
              return (
                <button
                  key={item.step}
                  onClick={() => {
                    if (item.step === 1) window.location.hash = "#/scope";
                    else setSelectedStep(item.step);
                  }}
                  className={`group mb-1 flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm ${
                    active ? "bg-white/5 ring-1 ring-white/10" : "hover:bg-white/5"
                  }`}
                >
                  <span
                    className={`grid h-7 w-7 place-items-center rounded-lg text-xs ${
                      active
                        ? "bg-sky-500/15 text-sky-200 ring-1 ring-sky-500/25"
                        : "bg-white/5 text-slate-300 ring-1 ring-white/10"
                    }`}
                  >
                    {item.step}
                  </span>
                  <span className={`${active ? "text-slate-50" : "text-slate-200"}`}>{item.name}</span>
                </button>
              );
            })}
          </nav>

          <button
            onClick={() => (window.location.hash = "#/dashboard")}
            className="mx-4 mt-6 mb-4 w-[calc(100%-2rem)] rounded-xl bg-indigo-600/90 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 transition"
          >
            Dashboard
          </button>
        </aside>

        {/* Main */}
        <main className="flex-1">
          <header className="sticky top-0 z-20 border-b border-white/10 bg-[#070A12]/70 backdrop-blur">
            <div className="mx-auto flex max-w-6xl items-center justify-center px-6 py-6">
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-100 text-center">
                ISO 27001 Audit Readiness Dashboard
              </h1>
            </div>
          </header>

          <div className="mx-auto max-w-6xl space-y-6 px-6 py-6">
            {/* Audit Scope line */}
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3">
                  <div className="text-xl text-slate-300">Audit Scope:</div>

                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <select
                        value={displayScopeName}
                        disabled
                        aria-label="Audit Scope"
                        className="appearance-none rounded-xl bg-white/5 px-4 py-2 pr-10 text-sm text-slate-100 ring-1 ring-white/10 border border-white/10 opacity-90 cursor-not-allowed"
                      >
                        <option value={displayScopeName}>{displayScopeName}</option>
                      </select>
                      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    </div>

                    <span className="text-sm text-slate-300">- ({displayAssetCount} assets)</span>

                    <Pill tone={labelTone(scopeSectionStatus)}>
                      <StatusDot status={scopeSectionStatus} />
                      {scopeSectionStatus}
                    </Pill>
                  </div>
                </div>

                {/* ✅ Section 2 items (only when In Progress / Completed) */}
                {!isScopeUnavailable ? (
                  <div className="rounded-2xl bg-white/5 p-4 ring-1 ring-white/10 border border-white/10">
                    <div className="text-sm font-semibold text-slate-100">Scope & Context — Section 2 (Organizational Boundaries)</div>
                    <div className="mt-2 text-sm text-slate-300">
                      {section2Items.length === 0 ? (
                        <span>NA</span>
                      ) : (
                        <ul className="list-disc pl-5 space-y-1">
                          {section2Items.map((x, idx) => (
                            <li key={idx}>{x}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                ) : null}
              </div>

              <div>
                <button
                  className="inline-flex items-center gap-2 rounded-xl bg-indigo-600/90 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600"
                  onClick={() => {
                    window.location.hash = "#/scope";
                  }}
                >
                  <Plus className="h-4 w-4" />
                  Start New Audit
                </button>
              </div>
            </div>

            {/* KPI row */}
            {data ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                <Card accent="amber">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm text-slate-300">Audit Readiness Score</div>
                      <div className="mt-2 text-4xl font-semibold">
                        {data.kpis.readiness_score.value}
                        <span className="text-slate-400">/{data.kpis.readiness_score.max}</span>
                      </div>
                      <div className="mt-2 text-sm text-slate-300">
                        {data.kpis.readiness_score.label} •{" "}
                        <span className="text-slate-100">
                          {data.kpis.readiness_score.delta_7d >= 0 ? "+" : ""}
                          {data.kpis.readiness_score.delta_7d}
                        </span>{" "}
                        in 7 days
                      </div>
                      <MiniBar
                        tone="amber"
                        valuePct={(data.kpis.readiness_score.value / data.kpis.readiness_score.max) * 100}
                      />
                    </div>
                    <div className="grid h-12 w-12 place-items-center rounded-2xl bg-amber-500/15 ring-1 ring-amber-500/25">
                      <BadgeCheck className="h-6 w-6 text-amber-200" />
                    </div>
                  </div>
                </Card>

                <Card accent="emerald">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm text-slate-300">Evidence Coverage</div>
                      <div className="mt-2 text-4xl font-semibold">{data.kpis.evidence_coverage.percent.toFixed(1)}%</div>
                      <div className="mt-2 text-sm text-slate-300">
                        {data.kpis.evidence_coverage.have}/{data.kpis.evidence_coverage.total} controls have evidence
                      </div>
                      <MiniBar tone="emerald" valuePct={data.kpis.evidence_coverage.percent} />
                    </div>
                    <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-500/15 ring-1 ring-emerald-500/25">
                      <CheckCircle2 className="h-6 w-6 text-emerald-200" />
                    </div>
                  </div>
                </Card>

                <Card accent="rose">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm text-slate-300">Open High/Critical Risks</div>
                      <div className="mt-2 text-4xl font-semibold">{data.kpis.open_high_critical.count}</div>
                      <div className="mt-2 text-sm text-rose-200">
                        {data.kpis.open_high_critical.unresolved} unresolved risks
                      </div>
                      <MiniBar tone="rose" valuePct={Math.min(100, data.kpis.open_high_critical.count * 5)} />
                    </div>
                    <div className="grid h-12 w-12 place-items-center rounded-2xl bg-rose-500/15 ring-1 ring-rose-500/25">
                      <AlertTriangle className="h-6 w-6 text-rose-200" />
                    </div>
                  </div>
                </Card>

                <Card accent="amber">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-sm text-slate-300">SoA Status</div>
                      <div className="mt-2 text-4xl font-semibold">{data.kpis.soa.status}</div>
                      <div className="mt-2 text-sm text-slate-300">
                        {data.kpis.soa.label} • {data.kpis.soa.pending_approvals} pending approvals
                      </div>
                      <MiniBar tone="amber" valuePct={Math.min(100, data.kpis.soa.pending_approvals * 7)} />
                    </div>
                    <div className="grid h-12 w-12 place-items-center rounded-2xl bg-amber-500/15 ring-1 ring-amber-500/25">
                      <FileText className="h-6 w-6 text-amber-200" />
                    </div>
                  </div>
                </Card>
              </div>
            ) : null}

            {/* Lifecycle */}
            <div className="rounded-2xl bg-white/5 p-6 ring-1 ring-white/10 border border-white/10">
              <div className="flex items-center justify-between">
                <div className="text-lg font-semibold">ISO 27001 Audit Lifecycle</div>
              </div>

              <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
                {lifecycle.map((s) => (
                  <div
                    key={s.step}
                    className={`flex items-center justify-between rounded-xl bg-white/5 px-4 py-3 ring-1 ring-white/10 ${
                      s.step === 11 ? "md:col-span-2" : ""
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="grid h-8 w-8 place-items-center rounded-full bg-white/10 ring-1 ring-white/10 text-xs">
                        {s.step}
                      </div>
                      <div className="text-sm text-slate-100">{s.name}</div>
                    </div>
                    <Pill tone={labelTone(s.status)}>{s.status}</Pill>
                  </div>
                ))}
              </div>
            </div>

            {err ? (
              <div className="rounded-xl bg-rose-500/10 px-4 py-3 text-sm text-rose-200 ring-1 ring-rose-500/20">
                Error: {err}
              </div>
            ) : null}
          </div>
        </main>
      </div>
    </div>
  );
}