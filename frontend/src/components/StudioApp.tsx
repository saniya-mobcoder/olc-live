"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import type {
  AuditEvent,
  Booking,
  EdgeScenario,
  ExecutiveReport,
  MarketingDraft,
  MatchRun,
  PoolAnalytics,
  Requirement,
  StageLyncPerson,
  Talent,
  WhatIfResult,
} from "@/lib/types";
import {
  AppHeader,
  Button,
  Field,
  Footer,
  Input,
  Select,
  Stat,
  Tabs,
  Textarea,
} from "@/components/ui";
import { ShortlistPanel, TalentDetailPane } from "./ShortlistPanel";
import { RejectedList } from "./RejectedList";
import { CopilotPanel } from "./CopilotPanel";

type NavId = "cast" | "discover" | "plan" | "ops" | "assist";
type DiscoverSub = "search" | "stagelync";
type PlanSub = "jobs" | "whatif";
type OpsSub = "bookings" | "reports" | "pool";
type AdvancedSub = "edges" | "audit" | null;

const NAV: { id: NavId; label: string }[] = [
  { id: "cast", label: "Cast" },
  { id: "discover", label: "Discover" },
  { id: "plan", label: "Plan" },
  { id: "ops", label: "Ops" },
  { id: "assist", label: "Assist" },
];

const CHART_FILL = "#8b5cf6";
const CHART_TICK = "#8b8fc4";

export function StudioApp() {
  const [nav, setNav] = useState<NavId>("cast");
  const [discoverSub, setDiscoverSub] = useState<DiscoverSub>("search");
  const [planSub, setPlanSub] = useState<PlanSub>("jobs");
  const [opsSub, setOpsSub] = useState<OpsSub>("bookings");
  const [advanced, setAdvanced] = useState<AdvancedSub>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [reqId, setReqId] = useState("REQ-0001");
  const [match, setMatch] = useState<MatchRun | null>(null);
  const [selectedTalent, setSelectedTalent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rankingMode, setRankingMode] = useState<"rules_only" | "hybrid">(
    "rules_only"
  );
  const [decisions, setDecisions] = useState<Record<string, string>>({});
  const [jobBrief, setJobBrief] = useState(
    "Desert Lights Spectacle\nLooking for: Aerial Artist in Dubai, UAE\nSkills: Aerial Silks, Trampoline\nLanguages: Arabic, English\nWeekly budget max $5500\nDates 2026-09-01 to 2026-10-15\nVisa sponsorship available."
  );
  const [jobFields, setJobFields] = useState<Record<string, unknown> | null>(
    null
  );
  const [jobWarnings, setJobWarnings] = useState<string[]>([]);
  const [jobMissing, setJobMissing] = useState<string[]>([]);
  const [jobSimilar, setJobSimilar] = useState<
    { requirement_id: string; production_title: string; similarity: number }[]
  >([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [marketingDraft, setMarketingDraft] = useState<MarketingDraft | null>(
    null
  );
  const [copilotMode, setCopilotMode] = useState<"match" | "support">("match");
  const [searchQ, setSearchQ] = useState("elite aerial artists UAE Arabic");
  const [searchHits, setSearchHits] = useState<Talent[]>([]);
  const [scoreAgainstResult, setScoreAgainstResult] = useState<{
    talentId: string;
    eligible: boolean;
    score: number | null;
    match_category: string;
    failed_gates: string[];
  } | null>(null);
  const [analytics, setAnalytics] = useState<PoolAnalytics | null>(null);
  const [whatIf, setWhatIf] = useState<WhatIfResult | null>(null);
  const [sponsor, setSponsor] = useState(true);
  const [budget, setBudget] = useState(5000);
  const [explanations, setExplanations] = useState<Record<string, string>>({});
  const [whatIfSuggestions, setWhatIfSuggestions] = useState<
    {
      label: string;
      params_override: Record<string, unknown>;
      rationale: string;
    }[]
  >([]);
  const [aiCosts, setAiCosts] = useState<{
    call_count: number;
    total_cost_usd: number;
    by_provider: Record<string, number>;
    by_tier: Record<string, number>;
  } | null>(null);
  const [poolInsight, setPoolInsight] = useState<string | null>(null);
  const [chat, setChat] = useState<
    { role: "user" | "assistant"; text: string; sources?: string[] }[]
  >([
    {
      role: "assistant",
      text: "Ask me why a talent was rejected, or to summarize the shortlist. Run a match first.",
    },
  ]);
  const [chatInput, setChatInput] = useState("Why was TAL-0471 rejected?");
  const [edges, setEdges] = useState<EdgeScenario[]>([]);
  const [edgeOut, setEdgeOut] = useState("");
  const [audits, setAudits] = useState<AuditEvent[]>([]);
  const [periodStart, setPeriodStart] = useState("2026-01-01");
  const [periodEnd, setPeriodEnd] = useState("2026-12-31");
  const [execReport, setExecReport] = useState<ExecutiveReport | null>(null);
  const [reportList, setReportList] = useState<ExecutiveReport[]>([]);
  const [slPeople, setSlPeople] = useState<StageLyncPerson[]>([]);
  const [slQuery, setSlQuery] = useState("elite aerial UAE");
  const [slMessage, setSlMessage] = useState("");
  const [copilotOpenMobile, setCopilotOpenMobile] = useState(false);

  const requirement = useMemo(
    () => requirements.find((r) => r.requirement_id === reqId) || null,
    [requirements, reqId]
  );

  const selectedRow = useMemo(() => {
    if (!match) return null;
    return (
      match.shortlist.find((r) => r.talent_id === selectedTalent) ||
      match.shortlist[0] ||
      null
    );
  }, [match, selectedTalent]);

  useEffect(() => {
    api
      .requirements()
      .then((rows) => {
        setRequirements(rows);
        if (rows[0]) setReqId(rows[0].requirement_id);
      })
      .catch((e) => setError(String(e.message || e)));
    api.edges().then(setEdges).catch(() => undefined);
  }, []);

  async function runMatch() {
    setLoading(true);
    setError(null);
    setNav("cast");
    try {
      const data = await api.match(reqId, {
        ranking_mode: rankingMode,
        include_ml_signals: true,
      });
      setMatch(data);
      setExplanations({});
      setSelectedTalent(data.shortlist[0]?.talent_id || null);
      setAudits(await api.audit(data.id));
      const rows = await api.listDecisions(data.id);
      const map: Record<string, string> = {};
      for (const d of rows) map[d.talent_id] = d.decision;
      setDecisions(map);
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function explainTalent(talentId: string) {
    if (!match) return;
    try {
      const res = await api.explainMatch(match.id, talentId);
      setExplanations((prev) => ({ ...prev, [talentId]: res.explanation }));
      setAudits(await api.audit(match.id));
    } catch (e) {
      setError(String((e as Error).message || e));
    }
  }

  async function recordDecision(
    talentId: string,
    decision: "hire" | "hold" | "reject"
  ) {
    if (!match) return;
    try {
      const row = await api.recordDecision(match.id, talentId, decision);
      setDecisions((prev) => ({ ...prev, [talentId]: row.decision }));
      setAudits(await api.audit(match.id));
    } catch (e) {
      setError(String((e as Error).message || e));
    }
  }

  async function parseJobBrief() {
    setLoading(true);
    setError(null);
    try {
      const parsed = await api.parseJob(jobBrief);
      setJobFields(parsed.fields);
      setJobWarnings(parsed.warnings);
      setJobMissing(parsed.missing_fields);
      const dedupe = await api.dedupeJob(
        jobBrief,
        String(parsed.fields.production_title || "")
      );
      setJobSimilar(dedupe.similar);
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function confirmJobBrief() {
    if (!jobFields) return;
    setLoading(true);
    setError(null);
    try {
      const req = await api.confirmJob(jobFields);
      setRequirements(await api.requirements());
      setReqId(req.requirement_id);
      setNav("cast");
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function loadBookings() {
    try {
      setBookings(await api.listBookings());
    } catch (e) {
      setError(String((e as Error).message || e));
    }
  }

  async function createBookingFromHire(talentId: string) {
    if (!match) return;
    setLoading(true);
    try {
      if (decisions[talentId] !== "hire") {
        await api.recordDecision(match.id, talentId, "hire");
        setDecisions((prev) => ({ ...prev, [talentId]: "hire" }));
      }
      await api.createBooking(match.id, talentId);
      await loadBookings();
      setNav("ops");
      setOpsSub("bookings");
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function generateMarketing(channel: "linkedin" | "newsletter") {
    setLoading(true);
    try {
      const bookingId = bookings[0]?.id;
      setMarketingDraft(
        await api.marketingDraft(
          bookingId
            ? { channel, booking_id: bookingId }
            : { channel, match_run_id: match?.id }
        )
      );
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function runSearch() {
    setLoading(true);
    setScoreAgainstResult(null);
    try {
      setSearchHits(await api.search(searchQ));
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function scoreHitAgainstReq(talentId: string) {
    setLoading(true);
    try {
      const res = await api.scoreAgainst(talentId, reqId);
      setScoreAgainstResult({
        talentId: res.talent_id,
        eligible: res.eligible,
        score: res.score,
        match_category: res.match_category,
        failed_gates: res.failed_gates,
      });
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function loadAnalytics() {
    setLoading(true);
    try {
      setAnalytics(await api.analytics());
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function runWhatIf() {
    setLoading(true);
    try {
      setWhatIf(
        await api.whatIf(reqId, {
          visa_sponsorship_available: sponsor,
          weekly_budget_max_usd: budget,
        })
      );
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function loadWhatIfSuggestions() {
    setLoading(true);
    try {
      const res = await api.suggestWhatIf(reqId);
      setWhatIfSuggestions(res.scenarios || []);
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function sendChat(override?: string) {
    const message = (override ?? chatInput).trim();
    if (!message) return;
    if (copilotMode === "match" && !match?.id) {
      setChat((c) => [
        ...c,
        { role: "user", text: message },
        {
          role: "assistant",
          text: "Run a match first, then ask about the shortlist or a rejection.",
        },
      ]);
      setChatInput("");
      return;
    }
    setChat((c) => [...c, { role: "user", text: message }]);
    setChatInput("");
    try {
      const res = await api.copilot(message, {
        mode: copilotMode,
        match_run_id: copilotMode === "match" ? match?.id : undefined,
        talent_id:
          copilotMode === "match" ? selectedTalent || undefined : undefined,
      });
      setChat((c) => [
        ...c,
        { role: "assistant", text: res.reply, sources: res.sources },
      ]);
    } catch (e) {
      setChat((c) => [
        ...c,
        { role: "assistant", text: String((e as Error).message || e) },
      ]);
    }
  }

  async function runEdge(id: string) {
    setLoading(true);
    try {
      setEdgeOut(JSON.stringify(await api.runEdge(id), null, 2));
    } catch (e) {
      setEdgeOut(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function generateReport() {
    setLoading(true);
    setError(null);
    try {
      setExecReport(await api.generateReport(periodStart, periodEnd, true));
      setReportList(await api.listReports());
      setAiCosts(await api.aiCosts());
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function syncStageLync() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.stagelyncSync();
      setSlMessage(res.message);
      setSlPeople(await api.stagelyncPeople());
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function discoverStageLync() {
    setLoading(true);
    try {
      setSlPeople(await api.stagelyncDiscover(slQuery));
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  async function importStageLync(id: string) {
    setLoading(true);
    try {
      const res = await api.stagelyncImport(id);
      setSlMessage(`Imported ${res.stagelync_person_id} → ${res.talent_id}`);
      setSlPeople(await api.stagelyncPeople());
    } catch (e) {
      setError(String((e as Error).message || e));
    } finally {
      setLoading(false);
    }
  }

  function onNavChange(id: NavId) {
    setNav(id);
    setAdvanced(null);
    if (id === "ops") {
      if (opsSub === "bookings") loadBookings();
      if (opsSub === "pool") loadAnalytics();
      if (opsSub === "reports") {
        api.listReports().then(setReportList).catch(() => undefined);
      }
    }
    if (id === "discover" && discoverSub === "stagelync") {
      api.stagelyncPeople().then(setSlPeople).catch(() => undefined);
    }
  }

  const copilotProps = {
    mode: copilotMode,
    onModeChange: setCopilotMode,
    chat,
    chatInput,
    onChatInput: setChatInput,
    onSend: sendChat,
    matchId: match?.id,
  };

  return (
    <div className="min-h-screen">
      <AppHeader
        actions={
          <Button size="sm" variant="gold" onClick={runMatch} disabled={loading}>
            {loading ? "Matching…" : "Run match"}
          </Button>
        }
      />

      <div className="mx-auto max-w-7xl px-4 pb-4 pt-4 sm:px-6">
        <div className="card-surface flex flex-col gap-4 p-4 md:flex-row md:items-end md:justify-between">
          <div className="max-w-xl">
            <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-cyan">
              Live talent intelligence
            </p>
            <h1 className="mt-1 font-display text-2xl text-ink md:text-3xl">
              Cast the shortlist you can defend
            </h1>
            <p className="mt-1 text-sm text-ink-muted">
              Hard gates first, then a clear 0–100 score — for live spectacle
              productions.
            </p>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <Field label="Requirement">
              <Select
                className="min-w-[16rem]"
                value={reqId}
                onChange={(e) => setReqId(e.target.value)}
              >
                {requirements.map((r) => (
                  <option key={r.requirement_id} value={r.requirement_id}>
                    {r.requirement_id} — {r.production_title}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Ranking">
              <Select
                className="min-w-[11rem]"
                value={rankingMode}
                onChange={(e) =>
                  setRankingMode(e.target.value as "rules_only" | "hybrid")
                }
              >
                <option value="rules_only">Rules only</option>
                <option value="hybrid">AI-assisted</option>
              </Select>
            </Field>
            <Button onClick={runMatch} disabled={loading}>
              {loading ? "Running…" : "Run match"}
            </Button>
          </div>
        </div>

        {loading ? (
          <p className="mt-3 text-center text-xs font-semibold uppercase tracking-eyebrow text-ink-muted">
            Gates → Score → Rank
          </p>
        ) : null}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <Tabs items={NAV} value={nav} onChange={onNavChange} />
          {nav === "cast" ? (
            <Button
              size="sm"
              variant="ghost"
              className="lg:hidden"
              onClick={() => setCopilotOpenMobile((v) => !v)}
            >
              {copilotOpenMobile ? "Hide assist" : "Assist"}
            </Button>
          ) : null}
        </div>

        {error ? (
          <div className="mt-4 rounded-xl border border-danger bg-danger-bg px-4 py-3 text-sm text-danger-fg">
            {error}
          </div>
        ) : null}
      </div>

      <main className="mx-auto max-w-7xl px-4 pb-16 sm:px-6">
        {nav === "cast" && (
          <section className="space-y-5">
            {match && requirement ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-ink-muted">
                      {match.id} · {match.eligible_count} eligible ·{" "}
                      {match.rejected_count} gated
                    </p>
                    <div className="mt-1 grid gap-2 text-sm text-ink-soft sm:grid-cols-2 lg:grid-cols-4">
                      <Meta label="Role" value={requirement.required_primary_role} />
                      <Meta
                        label="Window"
                        value={`${requirement.rehearsal_start_date} → ${requirement.performance_end_date}`}
                      />
                      <Meta
                        label="Venue"
                        value={`${requirement.city}, ${requirement.country}`}
                      />
                      <Meta
                        label="Budget"
                        value={`$${requirement.weekly_budget_max_usd}`}
                      />
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(["pdf", "xlsx", "csv", "json", "stagelync"] as const).map(
                      (ext) => (
                        <a
                          key={ext}
                          className="rounded-full border border-line-strong bg-white/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-ink-soft hover:border-cyan"
                          href={api.exportUrl(match.id, ext)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {ext === "stagelync" ? "StageLync" : ext}
                        </a>
                      )
                    )}
                  </div>
                </div>

                <div className="grid gap-5 lg:grid-cols-[0.95fr_1.1fr_0.85fr]">
                  <div className="space-y-4">
                    <ShortlistPanel
                      requirement={requirement}
                      shortlist={match.shortlist}
                      selectedId={selectedTalent}
                      onSelect={setSelectedTalent}
                      onDecision={recordDecision}
                      decisions={decisions}
                      onExplain={explainTalent}
                      explanations={explanations}
                      compact
                    />
                    <RejectedList
                      rejected={match.rejected}
                      onExplain={explainTalent}
                      explanations={explanations}
                    />
                  </div>
                  <TalentDetailPane
                    requirement={requirement}
                    shortlist={match.shortlist}
                    selected={selectedRow}
                  />
                  <div
                    className={`${copilotOpenMobile ? "block" : "hidden"} lg:block`}
                  >
                    <CopilotPanel {...copilotProps} compact />
                  </div>
                </div>
              </>
            ) : (
              <div className="card-surface flex flex-col items-center justify-center gap-4 px-6 py-20 text-center">
                <p className="font-display text-2xl text-ink">
                  Run a match to cast
                </p>
                <p className="max-w-md text-sm text-ink-muted">
                  Pick a requirement above, then run match. Eligible talent
                  lands in a ranked shortlist you can explain and decide on.
                </p>
                <Button onClick={runMatch} disabled={loading}>
                  Run match
                </Button>
              </div>
            )}

            <div className="pt-2">
              <button
                type="button"
                className="text-xs font-semibold uppercase tracking-eyebrow text-ink-muted hover:text-cyan"
                onClick={() => setShowAdvanced((v) => !v)}
              >
                {showAdvanced ? "Hide advanced" : "Advanced · edges & audit"}
              </button>
              {showAdvanced ? (
                <div className="mt-3 space-y-4">
                  <Tabs
                    items={[
                      { id: "edges", label: "Edge cases" },
                      { id: "audit", label: "Audit" },
                    ]}
                    value={advanced || "edges"}
                    onChange={(id) => setAdvanced(id as AdvancedSub)}
                  />
                  {(advanced || "edges") === "edges" ? (
                    <div className="space-y-3">
                      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                        {edges.map((e) => (
                          <button
                            key={e.id}
                            type="button"
                            onClick={() => runEdge(e.id)}
                            className="card-surface px-4 py-3 text-left hover:border-cyan/40"
                          >
                            <p className="text-[10px] uppercase tracking-eyebrow text-ink-muted">
                              {e.id}
                            </p>
                            <p className="mt-1 text-sm text-ink">{e.name}</p>
                          </button>
                        ))}
                      </div>
                      {edgeOut ? (
                        <pre className="card-surface overflow-x-auto p-4 text-xs text-ink-soft">
                          {edgeOut}
                        </pre>
                      ) : null}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {!match ? (
                        <p className="text-sm text-ink-muted">
                          Run a match to populate the audit trail.
                        </p>
                      ) : (
                        audits.map((a) => (
                          <div key={a.id} className="card-surface px-4 py-3 text-sm">
                            <p className="text-[10px] uppercase tracking-eyebrow text-ink-muted">
                              {a.event_type}
                              {a.talent_id ? ` · ${a.talent_id}` : ""}
                            </p>
                            <p className="mt-1 text-ink-soft">{a.message}</p>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </section>
        )}

        {nav === "discover" && (
          <section className="space-y-5">
            <Tabs
              items={[
                { id: "search", label: "Search" },
                { id: "stagelync", label: "StageLync" },
              ]}
              value={discoverSub}
              onChange={(id) => {
                setDiscoverSub(id);
                if (id === "stagelync") {
                  api.stagelyncPeople().then(setSlPeople).catch(() => undefined);
                }
              }}
            />
            {discoverSub === "search" ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {[
                    "elite aerial artists UAE Arabic",
                    "stunt performers London",
                    "aquatic divers Dubai",
                  ].map((q) => (
                    <Button
                      key={q}
                      size="sm"
                      variant="subtle"
                      onClick={async () => {
                        setSearchQ(q);
                        setLoading(true);
                        try {
                          setSearchHits(await api.search(q));
                        } catch (e) {
                          setError(String((e as Error).message || e));
                        } finally {
                          setLoading(false);
                        }
                      }}
                    >
                      {q}
                    </Button>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Input
                    className="min-w-[16rem] flex-1"
                    value={searchQ}
                    onChange={(e) => setSearchQ(e.target.value)}
                  />
                  <Button onClick={runSearch} disabled={loading}>
                    Search
                  </Button>
                </div>
                {scoreAgainstResult ? (
                  <div className="card-surface border-cyan/30 p-4 text-sm">
                    <p className="text-[11px] uppercase tracking-eyebrow text-cyan">
                      Score vs {reqId}
                    </p>
                    <p className="mt-1 text-ink">
                      {scoreAgainstResult.talentId} ·{" "}
                      {scoreAgainstResult.eligible ? "Eligible" : "Not eligible"}{" "}
                      · {scoreAgainstResult.score ?? "—"} ·{" "}
                      {scoreAgainstResult.match_category}
                    </p>
                    {scoreAgainstResult.failed_gates.length ? (
                      <p className="mt-2 text-ink-muted">
                        Gates: {scoreAgainstResult.failed_gates.join(", ")}
                      </p>
                    ) : (
                      <p className="mt-2 text-ink-muted">All hard gates passed.</p>
                    )}
                  </div>
                ) : null}
                <div className="grid gap-3 sm:grid-cols-2">
                  {searchHits.map((t) => (
                    <div key={t.talent_id} className="card-surface p-4">
                      <p className="text-[10px] uppercase tracking-eyebrow text-ink-muted">
                        {t.talent_id}
                      </p>
                      <h3 className="mt-1 font-display text-lg text-ink">
                        {t.full_name}
                      </h3>
                      <p className="text-sm text-ink-muted">
                        {t.primary_role} · {t.city}, {t.country}
                      </p>
                      <p className="mt-2 text-xs text-ink-soft">
                        {(t.languages || []).join(", ")} ·{" "}
                        {(t.primary_skills || []).slice(0, 4).join(", ")}
                      </p>
                      <Button
                        size="sm"
                        variant="outline"
                        className="mt-3"
                        onClick={() => scoreHitAgainstReq(t.talent_id)}
                      >
                        Score against {reqId}
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="card-surface flex flex-wrap items-end gap-3 p-4">
                  <Button onClick={syncStageLync} disabled={loading}>
                    Sync fixture
                  </Button>
                  <Input
                    className="min-w-[14rem] flex-1"
                    value={slQuery}
                    onChange={(e) => setSlQuery(e.target.value)}
                  />
                  <Button variant="outline" onClick={discoverStageLync}>
                    Discover
                  </Button>
                  <Button variant="ghost" onClick={() => setNav("cast")}>
                    Open Match
                  </Button>
                </div>
                {slMessage ? (
                  <p className="text-sm text-success-fg">{slMessage}</p>
                ) : null}
                <div className="grid gap-3 sm:grid-cols-2">
                  {slPeople.map((p) => (
                    <div key={p.stagelync_person_id} className="card-surface p-4">
                      <p className="text-[10px] uppercase tracking-eyebrow text-ink-muted">
                        {p.stagelync_person_id} · {p.link_status}
                      </p>
                      <h3 className="mt-1 font-display text-lg text-ink">
                        {p.display_name}
                      </h3>
                      <p className="text-sm text-ink-muted">
                        {p.primary_role} · ${p.weekly_rate_usd}
                      </p>
                      <p className="mt-2 text-xs text-ink-soft">
                        {(p.skills || []).slice(0, 5).join(", ")}
                      </p>
                      <Button
                        size="sm"
                        className="mt-3"
                        disabled={p.link_status === "imported"}
                        onClick={() => importStageLync(p.stagelync_person_id)}
                      >
                        {p.link_status === "imported"
                          ? "Already in OLC"
                          : "Import to OLC"}
                      </Button>
                    </div>
                  ))}
                </div>
                {!slPeople.length ? (
                  <p className="card-surface p-6 text-sm text-ink-muted">
                    Sync the StageLync fixture, then discover and import people.
                  </p>
                ) : null}
              </div>
            )}
          </section>
        )}

        {nav === "plan" && (
          <section className="space-y-5">
            <Tabs
              items={[
                { id: "jobs", label: "Jobs" },
                { id: "whatif", label: "What-If" },
              ]}
              value={planSub}
              onChange={setPlanSub}
            />
            {planSub === "jobs" ? (
              <div className="space-y-4">
                <p className="text-sm text-ink-muted">
                  Paste a casting brief, parse into a requirement, then confirm
                  and run match.
                </p>
                <Textarea
                  className="min-h-[10rem]"
                  value={jobBrief}
                  onChange={(e) => setJobBrief(e.target.value)}
                />
                <div className="flex flex-wrap gap-2">
                  <Button onClick={parseJobBrief} disabled={loading}>
                    Parse brief
                  </Button>
                  <Button
                    variant="outline"
                    onClick={confirmJobBrief}
                    disabled={!jobFields}
                  >
                    Confirm → Match
                  </Button>
                </div>
                {jobWarnings.length ? (
                  <ul className="card-surface space-y-1 p-4 text-sm text-ink-soft">
                    {jobWarnings.map((w) => (
                      <li key={w}>Warning: {w}</li>
                    ))}
                  </ul>
                ) : null}
                {jobMissing.length ? (
                  <p className="text-sm text-danger-fg">
                    Missing: {jobMissing.join(", ")}
                  </p>
                ) : null}
                {jobSimilar.length ? (
                  <div className="card-surface space-y-2 p-4 text-sm">
                    <p className="text-[11px] uppercase tracking-eyebrow text-cyan">
                      Similar open requirements
                    </p>
                    {jobSimilar.map((s) => (
                      <p key={s.requirement_id}>
                        {s.requirement_id} — {s.production_title} (
                        {s.similarity})
                      </p>
                    ))}
                  </div>
                ) : null}
                {jobFields ? (
                  <div className="card-surface grid gap-3 p-4 md:grid-cols-2">
                    {[
                      "production_title",
                      "required_primary_role",
                      "city",
                      "country",
                      "weekly_budget_max_usd",
                      "rehearsal_start_date",
                      "performance_end_date",
                    ].map((key) => (
                      <Field key={key} label={key}>
                        <Input
                          value={String(jobFields[key] ?? "")}
                          onChange={(e) =>
                            setJobFields({
                              ...jobFields,
                              [key]: e.target.value,
                            })
                          }
                        />
                      </Field>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="card-surface flex flex-wrap items-end gap-4 p-4">
                  <label className="flex items-center gap-2 text-sm text-ink-soft">
                    <input
                      type="checkbox"
                      checked={sponsor}
                      onChange={(e) => setSponsor(e.target.checked)}
                    />
                    Allow visa sponsorship
                  </label>
                  <Field label="Weekly budget max (USD)">
                    <Input
                      type="number"
                      value={budget}
                      onChange={(e) => setBudget(Number(e.target.value))}
                    />
                  </Field>
                  <Button onClick={runWhatIf} disabled={loading}>
                    Compare scenarios
                  </Button>
                  <Button variant="outline" onClick={loadWhatIfSuggestions}>
                    Suggest scenarios
                  </Button>
                </div>
                {whatIfSuggestions.length ? (
                  <div className="card-surface space-y-2 p-4">
                    <p className="text-[11px] uppercase tracking-eyebrow text-cyan">
                      AI suggestions
                    </p>
                    {whatIfSuggestions.map((s) => (
                      <button
                        key={s.label}
                        type="button"
                        className="block w-full rounded-xl border border-line bg-white/[0.03] px-3 py-2 text-left text-sm hover:border-cyan/40"
                        onClick={() => {
                          const p = s.params_override || {};
                          if (typeof p.visa_sponsorship_available === "boolean") {
                            setSponsor(Boolean(p.visa_sponsorship_available));
                          }
                          if (typeof p.weekly_budget_max_usd === "number") {
                            setBudget(Number(p.weekly_budget_max_usd));
                          }
                        }}
                      >
                        <strong className="text-ink">{s.label}</strong>
                        <span className="mt-1 block text-ink-muted">
                          {s.rationale}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : null}
                {whatIf ? (
                  <div className="grid gap-4 md:grid-cols-2">
                    <ScenarioCard title="Baseline" run={whatIf.baseline} />
                    <ScenarioCard title="Scenario" run={whatIf.scenario} />
                    <div className="card-surface p-4 md:col-span-2">
                      <p className="text-lg text-ink">
                        Eligible delta:{" "}
                        <strong>
                          {whatIf.eligible_delta >= 0 ? "+" : ""}
                          {whatIf.eligible_delta}
                        </strong>
                      </p>
                      <p className="mt-2 text-sm text-ink-muted">
                        Newly eligible:{" "}
                        {whatIf.new_talent_ids.join(", ") || "—"}
                      </p>
                      <p className="text-sm text-ink-muted">
                        Lost: {whatIf.lost_talent_ids.join(", ") || "—"}
                      </p>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </section>
        )}

        {nav === "ops" && (
          <section className="space-y-5">
            <Tabs
              items={[
                { id: "bookings", label: "Bookings" },
                { id: "reports", label: "Reports" },
                { id: "pool", label: "Pool" },
              ]}
              value={opsSub}
              onChange={(id) => {
                setOpsSub(id);
                if (id === "bookings") loadBookings();
                if (id === "pool") loadAnalytics();
                if (id === "reports") {
                  api.listReports().then(setReportList).catch(() => undefined);
                }
              }}
            />
            {opsSub === "bookings" ? (
              <div className="space-y-6">
                <p className="text-sm text-ink-muted">
                  Create bookings from hired shortlist talent and draft
                  marketing copy.
                </p>
                {match?.shortlist.length ? (
                  <div className="card-surface space-y-2 p-4">
                    <p className="text-[11px] uppercase tracking-eyebrow text-cyan">
                      From current match
                    </p>
                    {match.shortlist.map((r) => (
                      <div
                        key={r.talent_id}
                        className="flex flex-wrap items-center justify-between gap-2 border-b border-line py-2 text-sm"
                      >
                        <span className="text-ink">
                          {r.talent?.full_name}{" "}
                          <span className="text-ink-muted">
                            ({decisions[r.talent_id] || "undecided"})
                          </span>
                        </span>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => createBookingFromHire(r.talent_id)}
                        >
                          Create booking
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="card-surface p-4 text-sm text-ink-muted">
                    Run a match and mark Hire to create bookings.
                  </p>
                )}
                <div className="space-y-2">
                  {bookings.map((b) => (
                    <div
                      key={b.id}
                      className="card-surface flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm"
                    >
                      <div>
                        <p className="font-medium text-ink">
                          {b.id} · {b.talent_name || b.talent_id}
                        </p>
                        <p className="text-ink-muted">
                          {b.production_title} · ${b.weekly_rate_usd} ·{" "}
                          {b.start_date} → {b.end_date}
                        </p>
                      </div>
                      <a
                        className="rounded-full border border-line-strong px-3 py-1.5 text-xs uppercase tracking-wider text-ink-soft hover:border-cyan"
                        href={api.callsheetUrl(b.id)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Call sheet PDF
                      </a>
                    </div>
                  ))}
                  {!bookings.length ? (
                    <p className="text-sm text-ink-muted">No bookings yet.</p>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() => generateMarketing("linkedin")}
                    disabled={loading}
                  >
                    Draft LinkedIn
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => generateMarketing("newsletter")}
                    disabled={loading}
                  >
                    Draft newsletter
                  </Button>
                </div>
                {marketingDraft ? (
                  <Textarea
                    readOnly
                    className="min-h-[8rem]"
                    value={marketingDraft.body}
                  />
                ) : null}
              </div>
            ) : null}
            {opsSub === "reports" ? (
              <div className="space-y-6">
                <div className="card-surface flex flex-wrap items-end gap-4 p-4">
                  <Field label="Period start">
                    <Input
                      type="date"
                      value={periodStart}
                      onChange={(e) => setPeriodStart(e.target.value)}
                    />
                  </Field>
                  <Field label="Period end">
                    <Input
                      type="date"
                      value={periodEnd}
                      onChange={(e) => setPeriodEnd(e.target.value)}
                    />
                  </Field>
                  <Button onClick={generateReport} disabled={loading}>
                    Generate pack
                  </Button>
                  <Button
                    variant="outline"
                    onClick={async () => {
                      try {
                        setAiCosts(await api.aiCosts());
                      } catch (e) {
                        setError(String((e as Error).message || e));
                      }
                    }}
                  >
                    AI cost summary
                  </Button>
                </div>
                {aiCosts ? (
                  <div className="card-surface p-4 text-sm">
                    <p className="text-[11px] uppercase tracking-eyebrow text-cyan">
                      Dual-provider AI spend (session)
                    </p>
                    <p className="mt-2 text-ink">
                      Calls: {aiCosts.call_count} · Est. cost: $
                      {aiCosts.total_cost_usd.toFixed(4)}
                    </p>
                    <p className="mt-1 text-ink-muted">
                      By provider:{" "}
                      {Object.entries(aiCosts.by_provider)
                        .map(([k, v]) => `${k}=$${v.toFixed(4)}`)
                        .join(" · ") || "—"}
                    </p>
                  </div>
                ) : null}
                {execReport ? (
                  <>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-[11px] uppercase tracking-eyebrow text-ink-muted">
                        {execReport.id} · {execReport.period_start} →{" "}
                        {execReport.period_end}
                      </p>
                      <div className="flex gap-2">
                        <a
                          className="rounded-full border border-line-strong px-3 py-1.5 text-xs uppercase tracking-wider"
                          href={api.reportExportUrl(execReport.id, "pdf")}
                          target="_blank"
                          rel="noreferrer"
                        >
                          PDF
                        </a>
                        <a
                          className="rounded-full border border-line-strong px-3 py-1.5 text-xs uppercase tracking-wider"
                          href={api.reportExportUrl(execReport.id, "xlsx")}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Excel
                        </a>
                      </div>
                    </div>
                    {execReport.payload.narrative?.narrative ? (
                      <p className="card-surface p-4 text-sm text-ink-soft">
                        {execReport.payload.narrative.narrative}
                      </p>
                    ) : null}
                    <div className="grid gap-4 md:grid-cols-3">
                      <Stat
                        label="Reqs opened"
                        value={
                          execReport.payload.operational?.requirements_opened ||
                          0
                        }
                      />
                      <Stat
                        label="Match runs"
                        value={execReport.payload.operational?.match_runs || 0}
                      />
                      <Stat
                        label="Top-5 fill %"
                        value={
                          execReport.payload.operational?.top5_fill_rate_pct ||
                          0
                        }
                      />
                      <Stat
                        label="Decision accept %"
                        value={
                          execReport.payload.operational
                            ?.decision_acceptance_pct || 0
                        }
                      />
                      <Stat
                        label="Contract value"
                        value={
                          execReport.payload.commercial?.contract_value_usd || 0
                        }
                      />
                      <Stat
                        label="Rehire share %"
                        value={
                          execReport.payload.commercial
                            ?.rehire_eligible_share_pct || 0
                        }
                      />
                    </div>
                    <div className="card-surface h-72 p-4">
                      <p className="mb-2 text-[11px] uppercase tracking-eyebrow text-ink-muted">
                        Gate fails
                      </p>
                      <ResponsiveContainer width="100%" height="90%">
                        <BarChart
                          data={
                            execReport.payload.operational
                              ?.gate_fail_frequency || []
                          }
                        >
                          <XAxis
                            dataKey="gate"
                            tick={{ fill: CHART_TICK, fontSize: 11 }}
                          />
                          <YAxis
                            allowDecimals={false}
                            tick={{ fill: CHART_TICK }}
                          />
                          <Tooltip
                            contentStyle={{
                              background: "#14163f",
                              border: "1px solid rgba(255,255,255,0.1)",
                            }}
                          />
                          <Bar dataKey="count" fill={CHART_FILL} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </>
                ) : null}
                {reportList.length ? (
                  <div className="space-y-2">
                    <p className="text-[11px] uppercase tracking-eyebrow text-ink-muted">
                      Recent packs
                    </p>
                    {reportList.map((r) => (
                      <button
                        key={r.id}
                        type="button"
                        className="card-surface block w-full px-4 py-3 text-left text-sm hover:border-cyan/40"
                        onClick={() => setExecReport(r)}
                      >
                        {r.id} · {r.period_start} → {r.period_end}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
            {opsSub === "pool" && analytics ? (
              <div className="space-y-6">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={async () => {
                    try {
                      const res = await api.poolNarrative();
                      setPoolInsight(res.narrative);
                    } catch (e) {
                      setError(String((e as Error).message || e));
                    }
                  }}
                >
                  Generate insight narrative
                </Button>
                {poolInsight ? (
                  <p className="card-surface p-4 text-sm text-ink-soft">
                    {poolInsight}
                  </p>
                ) : null}
                <div className="grid gap-4 md:grid-cols-3">
                  <Stat label="Talent" value={analytics.totals.talent_count} />
                  <Stat label="Elite" value={analytics.totals.elite_count} />
                  <Stat
                    label="Avg audition"
                    value={analytics.totals.avg_audition}
                  />
                </div>
                <div className="card-surface h-72 p-4">
                  <p className="mb-2 text-[11px] uppercase tracking-eyebrow text-ink-muted">
                    By role
                  </p>
                  <ResponsiveContainer width="100%" height="90%">
                    <BarChart data={analytics.by_role}>
                      <XAxis
                        dataKey="role"
                        tick={{ fill: CHART_TICK, fontSize: 11 }}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fill: CHART_TICK }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#14163f",
                          border: "1px solid rgba(255,255,255,0.1)",
                        }}
                      />
                      <Bar dataKey="count" fill={CHART_FILL} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <ul className="space-y-2 text-sm">
                  {analytics.gaps.map((g, i) => (
                    <li
                      key={String(g.insight || g.role || `gap-${i}`)}
                      className="card-surface px-4 py-3"
                    >
                      {String(g.insight || `${g.role}: count ${g.count}`)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {opsSub === "pool" && !analytics ? (
              <p className="text-sm text-ink-muted">Loading pool…</p>
            ) : null}
          </section>
        )}

        {nav === "assist" && (
          <section>
            <CopilotPanel {...copilotProps} />
          </section>
        )}
      </main>

      <Footer />
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-eyebrow text-ink-muted">
        {label}
      </p>
      <p className="mt-0.5 text-sm font-medium text-ink">{value}</p>
    </div>
  );
}

function ScenarioCard({ title, run }: { title: string; run: MatchRun }) {
  return (
    <div className="card-surface p-4">
      <h3 className="font-display text-xl text-ink">{title}</h3>
      <p className="text-xs text-ink-muted">
        {run.id} · eligible {run.eligible_count}
      </p>
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-ink-soft">
        {run.shortlist.map((r) => (
          <li key={r.talent_id}>
            {r.talent?.full_name} — {r.score}
          </li>
        ))}
      </ol>
    </div>
  );
}
