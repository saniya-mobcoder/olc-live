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
import { ShortlistPanel } from "./ShortlistPanel";
import { RejectedList } from "./RejectedList";

type Tab =
  | "match"
  | "jobs"
  | "search"
  | "analytics"
  | "reports"
  | "stagelync"
  | "whatif"
  | "ops"
  | "copilot"
  | "edges"
  | "audit";

const TABS: { id: Tab; label: string }[] = [
  { id: "match", label: "Match" },
  { id: "jobs", label: "Jobs" },
  { id: "search", label: "Search" },
  { id: "analytics", label: "Pool" },
  { id: "reports", label: "Reports" },
  { id: "stagelync", label: "StageLync" },
  { id: "whatif", label: "What-If" },
  { id: "ops", label: "Ops" },
  { id: "copilot", label: "Copilot" },
  { id: "edges", label: "Edge Cases" },
  { id: "audit", label: "Audit" },
];

export function StudioApp() {
  const [tab, setTab] = useState<Tab>("match");
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

  const [chat, setChat] = useState<{
    role: "user" | "assistant";
    text: string;
    sources?: string[];
  }[]>([
    {
      role: "assistant",
      text: "Ask me why a talent was rejected, or to summarize the shortlist. Run a match first.",
    },
  ]);
  const [chatInput, setChatInput] = useState("Why was TAL-0471 rejected?");

  const [edges, setEdges] = useState<EdgeScenario[]>([]);
  const [edgeOut, setEdgeOut] = useState<string>("");
  const [audits, setAudits] = useState<AuditEvent[]>([]);

  const [periodStart, setPeriodStart] = useState("2026-01-01");
  const [periodEnd, setPeriodEnd] = useState("2026-12-31");
  const [execReport, setExecReport] = useState<ExecutiveReport | null>(null);
  const [reportList, setReportList] = useState<ExecutiveReport[]>([]);

  const [slPeople, setSlPeople] = useState<StageLyncPerson[]>([]);
  const [slQuery, setSlQuery] = useState("elite aerial UAE");
  const [slMessage, setSlMessage] = useState("");

  const requirement = useMemo(
    () => requirements.find((r) => r.requirement_id === reqId) || null,
    [requirements, reqId]
  );

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
    try {
      const data = await api.match(reqId, { ranking_mode: rankingMode });
      setMatch(data);
      setSelectedTalent(data.shortlist[0]?.talent_id || null);
      const events = await api.audit(data.id);
      setAudits(events);
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
      const list = await api.requirements();
      setRequirements(list);
      setReqId(req.requirement_id);
      setTab("match");
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
      setTab("ops");
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
      const draft = await api.marketingDraft(
        bookingId
          ? { channel, booking_id: bookingId }
          : { channel, match_run_id: match?.id }
      );
      setMarketingDraft(draft);
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
      const data = await api.whatIf(reqId, {
        visa_sponsorship_available: sponsor,
        weekly_budget_max_usd: budget,
      });
      setWhatIf(data);
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
      const res = await api.runEdge(id);
      setEdgeOut(JSON.stringify(res, null, 2));
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
      const report = await api.generateReport(periodStart, periodEnd);
      setExecReport(report);
      setReportList(await api.listReports());
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

  return (
    <div className="min-h-screen">
      <header className="relative overflow-hidden border-b border-[var(--olc-ink)]/10">
        <div className="pointer-events-none absolute inset-0">
          <div className="animate-pulse-soft absolute -left-20 top-0 h-64 w-64 rounded-full bg-[var(--olc-leaf)]/15 blur-3xl" />
        </div>
        <div className="relative mx-auto flex max-w-7xl flex-col gap-8 px-6 pb-10 pt-8 md:flex-row md:items-end md:justify-between">
          <div className="animate-rise max-w-2xl">
            <p className="brand text-5xl tracking-tight text-[var(--olc-forest)] md:text-7xl">
              OLC
            </p>
            <h1 className="mt-2 text-2xl text-[var(--olc-ink)] md:text-3xl">
              Talent Matching
            </h1>
            <p className="mt-3 max-w-xl text-base text-[var(--olc-ink)]/70">
              Explainable shortlists for live productions — hard gates first,
              then a clear 0–100 score you can defend in the room.
            </p>
          </div>
          <div className="animate-rise-delay panel flex flex-wrap items-end gap-3 p-4">
            <label className="block text-xs uppercase tracking-[0.16em] text-[var(--olc-ink)]/55">
              Requirement
              <select
                className="mt-1 block min-w-[16rem] border border-[var(--olc-ink)]/15 bg-white/80 px-3 py-2 text-sm"
                value={reqId}
                onChange={(e) => setReqId(e.target.value)}
              >
                {requirements.map((r) => (
                  <option key={r.requirement_id} value={r.requirement_id}>
                    {r.requirement_id} — {r.production_title}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs uppercase tracking-[0.16em] text-[var(--olc-ink)]/55">
              Ranking
              <select
                className="mt-1 block min-w-[12rem] border border-[var(--olc-ink)]/15 bg-white/80 px-3 py-2 text-sm"
                value={rankingMode}
                onChange={(e) =>
                  setRankingMode(e.target.value as "rules_only" | "hybrid")
                }
              >
                <option value="rules_only">Rules only</option>
                <option value="hybrid">AI-assisted rank</option>
              </select>
            </label>
            <button
              type="button"
              onClick={runMatch}
              disabled={loading}
              className="bg-[var(--olc-forest)] px-5 py-2.5 text-sm uppercase tracking-[0.14em] text-[var(--olc-glow)] transition hover:bg-[var(--olc-leaf)] disabled:opacity-60"
            >
              {loading ? "Working…" : "Run match"}
            </button>
          </div>
        </div>
      </header>

      <nav className="sticky top-0 z-20 border-b border-[var(--olc-ink)]/10 bg-[var(--olc-paper)]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 py-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => {
                setTab(t.id);
                if (t.id === "analytics" && !analytics) loadAnalytics();
                if (t.id === "ops") loadBookings();
                if (t.id === "reports" && !reportList.length) {
                  api.listReports().then(setReportList).catch(() => undefined);
                }
                if (t.id === "stagelync" && !slPeople.length) {
                  api
                    .stagelyncPeople()
                    .then(setSlPeople)
                    .catch(() => undefined);
                }
              }}
              className={`whitespace-nowrap px-4 py-2 text-sm tracking-wide ${
                tab === t.id
                  ? "bg-[var(--olc-forest)] text-white"
                  : "text-[var(--olc-ink)]/70 hover:bg-white/60"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {error ? (
          <div className="mb-6 border border-[var(--olc-coral)] bg-[#f8ebe6] px-4 py-3 text-sm">
            {error} — Is the API running on :8000?
          </div>
        ) : null}

        {tab === "match" && (
          <section className="space-y-8">
            {requirement ? (
              <div className="panel grid gap-4 p-5 md:grid-cols-4">
                <Meta label="Role" value={requirement.required_primary_role} />
                <Meta
                  label="Window"
                  value={`${requirement.performance_start_date} → ${requirement.performance_end_date}`}
                />
                <Meta
                  label="Venue"
                  value={`${requirement.city}, ${requirement.country}`}
                />
                <Meta
                  label="Weekly budget max"
                  value={`USD ${requirement.weekly_budget_max_usd}`}
                />
              </div>
            ) : null}

            {match ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-[var(--olc-leaf)]">
                      {match.id} · {match.eligible_count} eligible ·{" "}
                      {match.rejected_count} rejected
                    </p>
                    <h2 className="text-3xl">Top 5 shortlist</h2>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {(["pdf", "xlsx", "csv", "json", "stagelync"] as const).map(
                      (ext) => (
                        <a
                          key={ext}
                          className="border border-[var(--olc-ink)]/20 bg-white/70 px-3 py-1.5 text-xs uppercase tracking-wider hover:border-[var(--olc-forest)]"
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
                {requirement ? (
                  <ShortlistPanel
                    requirement={requirement}
                    shortlist={match.shortlist}
                    selectedId={selectedTalent}
                    onSelect={setSelectedTalent}
                    onDecision={recordDecision}
                    decisions={decisions}
                  />
                ) : null}
                <div>
                  <h2 className="mb-3 text-2xl">Rejected with reasons</h2>
                  <RejectedList rejected={match.rejected} />
                </div>
              </>
            ) : (
              <p className="panel p-8 text-[var(--olc-ink)]/70">
                Choose a requirement and run a match to see ranked talent,
                score breakdowns, maps, and rejection reasons.
              </p>
            )}
          </section>
        )}

        {tab === "jobs" && (
          <section className="space-y-4">
            <h2 className="text-3xl">Job ingestion</h2>
            <p className="text-sm text-[var(--olc-ink)]/70">
              Paste a casting brief, parse into a structured requirement, check
              duplicates, then confirm and run match.
            </p>
            <textarea
              className="min-h-[10rem] w-full border border-[var(--olc-ink)]/15 bg-white/80 px-3 py-2 text-sm"
              value={jobBrief}
              onChange={(e) => setJobBrief(e.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={parseJobBrief}
                className="bg-[var(--olc-forest)] px-4 py-2 text-sm text-white"
              >
                Parse brief
              </button>
              <button
                type="button"
                onClick={confirmJobBrief}
                disabled={!jobFields}
                className="border border-[var(--olc-forest)] px-4 py-2 text-sm text-[var(--olc-forest)] disabled:opacity-50"
              >
                Confirm → Match
              </button>
            </div>
            {jobWarnings.length ? (
              <ul className="panel space-y-1 p-4 text-sm text-[var(--olc-ink)]/80">
                {jobWarnings.map((w) => (
                  <li key={w}>Warning: {w}</li>
                ))}
              </ul>
            ) : null}
            {jobMissing.length ? (
              <p className="text-sm text-[var(--olc-coral)]">
                Missing: {jobMissing.join(", ")}
              </p>
            ) : null}
            {jobSimilar.length ? (
              <div className="panel space-y-2 p-4 text-sm">
                <p className="text-xs uppercase tracking-wider text-[var(--olc-leaf)]">
                  Similar open requirements
                </p>
                {jobSimilar.map((s) => (
                  <p key={s.requirement_id}>
                    {s.requirement_id} · {s.production_title} · sim{" "}
                    {s.similarity}
                  </p>
                ))}
              </div>
            ) : null}
            {jobFields ? (
              <div className="panel grid gap-3 p-4 md:grid-cols-2">
                {(
                  [
                    "production_title",
                    "required_primary_role",
                    "required_category",
                    "city",
                    "country",
                    "rehearsal_start_date",
                    "performance_end_date",
                    "weekly_budget_max_usd",
                  ] as const
                ).map((key) => (
                  <label
                    key={key}
                    className="block text-xs uppercase tracking-wider text-[var(--olc-ink)]/55"
                  >
                    {key}
                    <input
                      className="mt-1 w-full border border-[var(--olc-ink)]/15 bg-white px-2 py-1.5 text-sm normal-case tracking-normal"
                      value={String(jobFields[key] ?? "")}
                      onChange={(e) =>
                        setJobFields((prev) =>
                          prev
                            ? {
                                ...prev,
                                [key]:
                                  key === "weekly_budget_max_usd"
                                    ? Number(e.target.value) || 0
                                    : e.target.value,
                              }
                            : prev
                        )
                      }
                    />
                  </label>
                ))}
              </div>
            ) : null}
          </section>
        )}

        {tab === "search" && (
          <section className="space-y-4">
            <h2 className="text-3xl">Natural language search</h2>
            <div className="flex flex-wrap gap-2">
              {(
                [
                  "elite aerial artists UAE Arabic",
                  "Arabic-speaking stunt",
                  "elite aquatic performer",
                ] as const
              ).map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className="border border-[var(--olc-ink)]/15 bg-white/70 px-3 py-1.5 text-xs uppercase tracking-wider hover:border-[var(--olc-forest)]"
                  onClick={() => {
                    setSearchQ(chip);
                    setTimeout(() => {
                      void (async () => {
                        setLoading(true);
                        setScoreAgainstResult(null);
                        try {
                          setSearchHits(await api.search(chip));
                        } catch (e) {
                          setError(String((e as Error).message || e));
                        } finally {
                          setLoading(false);
                        }
                      })();
                    }, 0);
                  }}
                >
                  {chip}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <input
                className="min-w-[20rem] flex-1 border border-[var(--olc-ink)]/15 bg-white/80 px-3 py-2"
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
              />
              <button
                type="button"
                onClick={runSearch}
                className="bg-[var(--olc-forest)] px-4 py-2 text-sm text-white"
              >
                Search
              </button>
            </div>
            {scoreAgainstResult ? (
              <div className="panel border border-[var(--olc-forest)]/30 p-4 text-sm">
                <p className="text-xs uppercase tracking-wider text-[var(--olc-leaf)]">
                  Score against {reqId} · {scoreAgainstResult.talentId}
                </p>
                <p className="mt-1 text-lg">
                  {scoreAgainstResult.eligible ? "Eligible" : "Not eligible"} ·{" "}
                  {scoreAgainstResult.score?.toFixed(1) ?? "—"} ·{" "}
                  {scoreAgainstResult.match_category}
                </p>
                {scoreAgainstResult.failed_gates.length ? (
                  <p className="mt-2 text-[var(--olc-ink)]/70">
                    Failed gates: {scoreAgainstResult.failed_gates.join(", ")}
                  </p>
                ) : (
                  <p className="mt-2 text-[var(--olc-ink)]/70">All hard gates passed.</p>
                )}
              </div>
            ) : null}
            <div className="grid gap-3 md:grid-cols-2">
              {searchHits.map((t) => (
                <div key={t.talent_id} className="panel p-4">
                  <p className="text-xs uppercase tracking-wider text-[var(--olc-leaf)]">
                    {t.talent_id}{" "}
                    {t.physical_skill_level === "Elite" ? "· Elite" : ""}
                  </p>
                  <h3 className="text-xl">{t.full_name}</h3>
                  <p className="text-sm text-[var(--olc-ink)]/70">
                    {t.primary_role} · {t.city}, {t.country} ·{" "}
                    {t.languages.join(", ")}
                  </p>
                  <p className="mt-2 text-sm">
                    {t.primary_skills.slice(0, 6).join(" · ")}
                  </p>
                  <button
                    type="button"
                    className="mt-3 border border-[var(--olc-forest)] px-3 py-1.5 text-xs uppercase tracking-wider text-[var(--olc-forest)]"
                    onClick={() => scoreHitAgainstReq(t.talent_id)}
                  >
                    Score against {reqId}
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {tab === "analytics" && analytics && (
          <section className="space-y-6">
            <h2 className="text-3xl">Talent pool insights</h2>
            <div className="grid gap-4 md:grid-cols-3">
              <Stat label="Talent" value={analytics.totals.talent_count} />
              <Stat label="Elite" value={analytics.totals.elite_count} />
              <Stat label="Avg audition" value={analytics.totals.avg_audition} />
            </div>
            <div className="panel h-72 p-4">
              <p className="mb-2 text-xs uppercase tracking-wider">By role</p>
              <ResponsiveContainer width="100%" height="90%">
                <BarChart data={analytics.by_role}>
                  <XAxis dataKey="role" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#0b3d2e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <ul className="space-y-2 text-sm">
              {analytics.gaps.map((g, i) => (
                <li
                  key={String(g.insight || g.role || `gap-${i}`)}
                  className="panel px-4 py-3"
                >
                  {String(g.insight || `${g.role}: count ${g.count}`)}
                </li>
              ))}
            </ul>
          </section>
        )}

        {tab === "reports" && (
          <section className="space-y-6">
            <h2 className="text-3xl">Executive reports</h2>
            <div className="panel flex flex-wrap items-end gap-4 p-4">
              <label className="text-xs uppercase tracking-wider">
                Period start
                <input
                  type="date"
                  className="mt-1 block border border-[var(--olc-ink)]/15 bg-white px-3 py-2"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                />
              </label>
              <label className="text-xs uppercase tracking-wider">
                Period end
                <input
                  type="date"
                  className="mt-1 block border border-[var(--olc-ink)]/15 bg-white px-3 py-2"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                />
              </label>
              <button
                type="button"
                onClick={generateReport}
                className="bg-[var(--olc-forest)] px-4 py-2 text-sm text-white"
              >
                Generate pack
              </button>
            </div>
            {execReport ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-[var(--olc-leaf)]">
                    {execReport.id} · {execReport.period_start} →{" "}
                    {execReport.period_end}
                  </p>
                  <div className="flex gap-2">
                    <a
                      className="border border-[var(--olc-ink)]/20 bg-white/70 px-3 py-1.5 text-xs uppercase tracking-wider"
                      href={api.reportExportUrl(execReport.id, "pdf")}
                      target="_blank"
                      rel="noreferrer"
                    >
                      PDF
                    </a>
                    <a
                      className="border border-[var(--olc-ink)]/20 bg-white/70 px-3 py-1.5 text-xs uppercase tracking-wider"
                      href={api.reportExportUrl(execReport.id, "xlsx")}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Excel
                    </a>
                  </div>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                  <Stat
                    label="Reqs opened"
                    value={
                      execReport.payload.operational?.requirements_opened || 0
                    }
                  />
                  <Stat
                    label="Match runs"
                    value={execReport.payload.operational?.match_runs || 0}
                  />
                  <Stat
                    label="Top-5 fill %"
                    value={
                      execReport.payload.operational?.top5_fill_rate_pct || 0
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
                    label="Contract value $"
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
                  <Stat
                    label="Budget vs rate $"
                    value={
                      execReport.payload.commercial?.budget_vs_rate_delta_usd ||
                      0
                    }
                  />
                </div>
                <div className="panel h-72 p-4">
                  <p className="mb-2 text-xs uppercase tracking-wider">
                    Gate fail frequency
                  </p>
                  <ResponsiveContainer width="100%" height="90%">
                    <BarChart
                      data={
                        execReport.payload.operational?.gate_fail_frequency ||
                        []
                      }
                    >
                      <XAxis dataKey="gate" tick={{ fontSize: 10 }} />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#c45c3e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </>
            ) : (
              <p className="panel p-6 text-sm text-[var(--olc-ink)]/70">
                Pick a period and generate an operational + commercial pack.
              </p>
            )}
            {reportList.length > 0 ? (
              <div className="space-y-2">
                <h3 className="text-xl">Recent reports</h3>
                {reportList.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    className="panel block w-full px-4 py-3 text-left text-sm"
                    onClick={() => setExecReport(r)}
                  >
                    {r.id} · {r.period_start} → {r.period_end}
                  </button>
                ))}
              </div>
            ) : null}
          </section>
        )}

        {tab === "stagelync" && (
          <section className="space-y-6">
            <h2 className="text-3xl">StageLync discovery</h2>
            <div className="panel flex flex-wrap items-end gap-3 p-4">
              <button
                type="button"
                onClick={syncStageLync}
                className="bg-[var(--olc-forest)] px-4 py-2 text-sm text-white"
              >
                Sync fixture
              </button>
              <input
                className="min-w-[16rem] flex-1 border border-[var(--olc-ink)]/15 bg-white px-3 py-2"
                value={slQuery}
                onChange={(e) => setSlQuery(e.target.value)}
                placeholder="Discover query"
              />
              <button
                type="button"
                onClick={discoverStageLync}
                className="border border-[var(--olc-forest)] px-4 py-2 text-sm text-[var(--olc-forest)]"
              >
                Discover
              </button>
              <button
                type="button"
                onClick={() => setTab("match")}
                className="border border-[var(--olc-ink)]/20 px-4 py-2 text-sm"
              >
                Open Match
              </button>
            </div>
            {slMessage ? (
              <p className="text-sm text-[var(--olc-leaf)]">{slMessage}</p>
            ) : null}
            <div className="grid gap-3 md:grid-cols-2">
              {slPeople.map((p) => (
                <div key={p.stagelync_person_id} className="panel p-4">
                  <p className="text-xs uppercase tracking-wider text-[var(--olc-leaf)]">
                    {p.stagelync_person_id} · {p.link_status}
                    {p.talent_id ? ` · ${p.talent_id}` : ""}
                  </p>
                  <h3 className="text-xl">{p.display_name}</h3>
                  <p className="text-sm text-[var(--olc-ink)]/70">
                    {p.primary_role} · {p.city}, {p.country} · $
                    {p.weekly_rate_usd}/wk
                  </p>
                  <p className="mt-2 text-sm">{p.skills.slice(0, 5).join(" · ")}</p>
                  <p className="mt-2 text-xs text-[var(--olc-ink)]/60">
                    {p.profile_summary}
                  </p>
                  <button
                    type="button"
                    disabled={p.link_status === "imported"}
                    onClick={() => importStageLync(p.stagelync_person_id)}
                    className="mt-3 bg-[var(--olc-forest)] px-3 py-1.5 text-xs uppercase tracking-wider text-white disabled:opacity-50"
                  >
                    {p.link_status === "imported"
                      ? "Already in OLC"
                      : "Import to OLC"}
                  </button>
                </div>
              ))}
            </div>
            {!slPeople.length ? (
              <p className="panel p-6 text-sm text-[var(--olc-ink)]/70">
                Sync the StageLync fixture, then discover and import people into
                the OLC talent pool for matching.
              </p>
            ) : null}
          </section>
        )}

        {tab === "whatif" && (
          <section className="space-y-4">
            <h2 className="text-3xl">What-if simulation</h2>
            <div className="panel flex flex-wrap items-end gap-4 p-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={sponsor}
                  onChange={(e) => setSponsor(e.target.checked)}
                />
                Allow visa sponsorship
              </label>
              <label className="text-xs uppercase tracking-wider">
                Weekly budget max (USD)
                <input
                  type="number"
                  className="mt-1 block border border-[var(--olc-ink)]/15 bg-white px-3 py-2"
                  value={budget}
                  onChange={(e) => setBudget(Number(e.target.value))}
                />
              </label>
              <button
                type="button"
                onClick={runWhatIf}
                className="bg-[var(--olc-forest)] px-4 py-2 text-sm text-white"
              >
                Compare scenarios
              </button>
            </div>
            {whatIf ? (
              <div className="grid gap-4 md:grid-cols-2">
                <ScenarioCard title="Baseline" run={whatIf.baseline} />
                <ScenarioCard title="Scenario" run={whatIf.scenario} />
                <div className="panel p-4 md:col-span-2">
                  <p className="text-lg">
                    Eligible delta:{" "}
                    <strong>
                      {whatIf.eligible_delta >= 0 ? "+" : ""}
                      {whatIf.eligible_delta}
                    </strong>
                  </p>
                  <p className="mt-2 text-sm">
                    Newly eligible: {whatIf.new_talent_ids.join(", ") || "—"}
                  </p>
                  <p className="text-sm">
                    Lost: {whatIf.lost_talent_ids.join(", ") || "—"}
                  </p>
                </div>
              </div>
            ) : null}
          </section>
        )}

        {tab === "ops" && (
          <section className="space-y-6">
            <h2 className="text-3xl">Production ops</h2>
            <p className="text-sm text-[var(--olc-ink)]/70">
              Create bookings from hired shortlist talent, download call sheets,
              and draft marketing copy.
            </p>
            {match?.shortlist.length ? (
              <div className="panel space-y-2 p-4">
                <p className="text-xs uppercase tracking-wider text-[var(--olc-leaf)]">
                  From current match {match.id}
                </p>
                {match.shortlist.map((row) => (
                  <div
                    key={row.talent_id}
                    className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--olc-ink)]/10 py-2 text-sm"
                  >
                    <span>
                      {row.talent?.full_name} · {row.talent_id}
                      {decisions[row.talent_id]
                        ? ` · ${decisions[row.talent_id]}`
                        : ""}
                    </span>
                    <button
                      type="button"
                      className="border border-[var(--olc-forest)] px-3 py-1 text-xs uppercase tracking-wider text-[var(--olc-forest)]"
                      onClick={() => createBookingFromHire(row.talent_id)}
                    >
                      Create booking
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="panel p-4 text-sm">
                Run a match first, then hire and create bookings here.
              </p>
            )}
            <div className="space-y-2">
              <h3 className="text-xl">Bookings / schedule</h3>
              {bookings.length === 0 ? (
                <p className="text-sm text-[var(--olc-ink)]/60">No bookings yet.</p>
              ) : (
                bookings.map((b) => (
                  <div
                    key={b.id}
                    className="panel flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm"
                  >
                    <div>
                      <p className="font-medium">
                        {b.id} · {b.talent_name || b.talent_id}
                      </p>
                      <p className="text-[var(--olc-ink)]/65">
                        {b.production_title} · {b.start_date} → {b.end_date} · $
                        {b.weekly_rate_usd}
                      </p>
                    </div>
                    <a
                      className="border border-[var(--olc-ink)]/20 bg-white/70 px-3 py-1.5 text-xs uppercase tracking-wider"
                      href={api.callsheetUrl(b.id)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Call sheet PDF
                    </a>
                  </div>
                ))
              )}
            </div>
            <div className="space-y-3">
              <h3 className="text-xl">Marketing drafts</h3>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="bg-[var(--olc-forest)] px-4 py-2 text-sm text-white"
                  onClick={() => generateMarketing("linkedin")}
                >
                  LinkedIn draft
                </button>
                <button
                  type="button"
                  className="border border-[var(--olc-forest)] px-4 py-2 text-sm text-[var(--olc-forest)]"
                  onClick={() => generateMarketing("newsletter")}
                >
                  Newsletter draft
                </button>
              </div>
              {marketingDraft ? (
                <textarea
                  className="min-h-[8rem] w-full border border-[var(--olc-ink)]/15 bg-white/80 px-3 py-2 text-sm"
                  readOnly
                  value={marketingDraft.body}
                />
              ) : null}
            </div>
          </section>
        )}

        {tab === "copilot" && (
          <section className="mx-auto max-w-3xl space-y-4">
            <h2 className="text-3xl">Producer copilot</h2>
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ["match", "Match"],
                  ["support", "Support"],
                ] as const
              ).map(([mode, label]) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setCopilotMode(mode)}
                  className={`px-3 py-1.5 text-xs uppercase tracking-wider ${
                    copilotMode === mode
                      ? "bg-[var(--olc-forest)] text-white"
                      : "border border-[var(--olc-ink)]/15 bg-white/70"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            {copilotMode === "match" ? (
              !match ? (
                <p className="panel p-4 text-sm text-[var(--olc-ink)]/70">
                  Run a match first so answers stay grounded on a real shortlist.
                </p>
              ) : (
                <p className="text-xs uppercase tracking-wider text-[var(--olc-leaf)]">
                  Grounded on {match.id}
                  {selectedTalent ? ` · focus ${selectedTalent}` : ""}
                </p>
              )
            ) : (
              <p className="text-xs uppercase tracking-wider text-[var(--olc-leaf)]">
                Support mode · FAQ grounded
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {(copilotMode === "match"
                ? ([
                    "Summarize the shortlist",
                    match?.rejected[0]
                      ? `Why was ${match.rejected[0].talent_id} rejected?`
                      : "Why was TAL-0471 rejected?",
                    match?.shortlist.length && match.shortlist.length >= 2
                      ? `Compare ${match.shortlist[0].talent_id} vs ${match.shortlist[1].talent_id}`
                      : "Compare top two shortlist talents",
                  ] as const)
                : ([
                    "How do I run a match?",
                    "What is hybrid ranking?",
                    "How do StageLync imports work?",
                  ] as const)
              ).map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="border border-[var(--olc-ink)]/15 bg-white/70 px-3 py-1.5 text-xs uppercase tracking-wider hover:border-[var(--olc-forest)]"
                  onClick={() => sendChat(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
            <div className="panel max-h-[28rem] space-y-3 overflow-y-auto p-4">
              {chat.map((m, i) => (
                <div
                  key={`${m.role}-${i}-${m.text.slice(0, 24)}`}
                  className={`whitespace-pre-wrap text-sm ${
                    m.role === "user"
                      ? "ml-8 border border-[var(--olc-forest)]/20 bg-[var(--olc-mint)]/40 px-3 py-2"
                      : "mr-8 bg-white/70 px-3 py-2"
                  }`}
                >
                  {m.text}
                  {m.sources && m.sources.length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.sources.map((s) => (
                        <span
                          key={s}
                          className="border border-[var(--olc-ink)]/15 px-2 py-0.5 text-[10px] uppercase tracking-wider text-[var(--olc-ink)]/60"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                className="flex-1 border border-[var(--olc-ink)]/15 bg-white px-3 py-2"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendChat()}
              />
              <button
                type="button"
                onClick={() => sendChat()}
                className="bg-[var(--olc-forest)] px-4 py-2 text-white"
              >
                Send
              </button>
            </div>
          </section>
        )}

        {tab === "edges" && (
          <section className="space-y-4">
            <h2 className="text-3xl">Deterministic edge cases</h2>
            <div className="grid gap-2 md:grid-cols-2">
              {edges.map((e) => (
                <button
                  key={e.id}
                  type="button"
                  onClick={() => runEdge(e.id)}
                  className="panel px-4 py-3 text-left hover:border-[var(--olc-forest)]"
                >
                  <p className="text-xs uppercase tracking-wider text-[var(--olc-leaf)]">
                    {e.id}
                  </p>
                  <p className="font-medium">{e.name}</p>
                </button>
              ))}
            </div>
            {edgeOut ? (
              <pre className="panel overflow-x-auto p-4 text-xs">{edgeOut}</pre>
            ) : null}
          </section>
        )}

        {tab === "audit" && (
          <section className="space-y-4">
            <h2 className="text-3xl">Match audit trail</h2>
            {!match ? (
              <p className="text-sm text-[var(--olc-ink)]/70">
                Run a match first to populate the audit log.
              </p>
            ) : (
              <div className="space-y-2">
                {audits.map((a) => (
                  <div key={a.id} className="panel px-4 py-3 text-sm">
                    <p className="text-xs uppercase tracking-wider text-[var(--olc-leaf)]">
                      {a.event_type}
                      {a.talent_id ? ` · ${a.talent_id}` : ""}
                    </p>
                    <p>{a.message}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.16em] text-[var(--olc-ink)]/50">
        {label}
      </p>
      <p className="mt-1 text-sm font-medium">{value}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="panel p-4">
      <p className="text-xs uppercase tracking-wider text-[var(--olc-ink)]/55">
        {label}
      </p>
      <p className="mt-1 text-3xl text-[var(--olc-forest)]">{value}</p>
    </div>
  );
}

function ScenarioCard({ title, run }: { title: string; run: MatchRun }) {
  return (
    <div className="panel p-4">
      <h3 className="text-xl">{title}</h3>
      <p className="text-xs text-[var(--olc-ink)]/55">
        {run.id} · eligible {run.eligible_count}
      </p>
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm">
        {run.shortlist.map((r) => (
          <li key={r.talent_id}>
            {r.talent?.full_name} — {r.score}
          </li>
        ))}
      </ol>
    </div>
  );
}
