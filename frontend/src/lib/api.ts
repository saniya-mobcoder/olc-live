import type {
  AuditEvent,
  Booking,
  EdgeScenario,
  ExecutiveReport,
  MarketingDraft,
  MatchDecision,
  MatchRun,
  PoolAnalytics,
  Requirement,
  ScoreAgainst,
  StageLyncPerson,
  Talent,
  WhatIfResult,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  requirements: () => request<Requirement[]>("/requirements"),
  talents: () => request<Talent[]>("/talents"),
  match: (requirementId: string, extras?: Record<string, unknown>) =>
    request<MatchRun>("/matches", {
      method: "POST",
      body: JSON.stringify({
        requirement_id: requirementId,
        top_k: 5,
        ...extras,
      }),
    }),
  getMatch: (id: string) => request<MatchRun>(`/matches/${id}`),
  recordDecision: (
    runId: string,
    talentId: string,
    decision: "hire" | "hold" | "reject",
    reason = ""
  ) =>
    request<MatchDecision>(`/matches/${runId}/decisions`, {
      method: "POST",
      body: JSON.stringify({
        talent_id: talentId,
        decision,
        reason,
      }),
    }),
  listDecisions: (runId: string) =>
    request<MatchDecision[]>(`/matches/${runId}/decisions`),
  search: (query: string) =>
    request<Talent[]>("/search/talents", {
      method: "POST",
      body: JSON.stringify({ query, limit: 20 }),
    }),
  scoreAgainst: (talentId: string, requirementId: string) =>
    request<ScoreAgainst>("/search/score-against", {
      method: "POST",
      body: JSON.stringify({
        talent_id: talentId,
        requirement_id: requirementId,
      }),
    }),
  parseJob: (brief_text: string) =>
    request<{
      fields: Record<string, unknown>;
      warnings: string[];
      missing_fields: string[];
    }>("/jobs/parse", {
      method: "POST",
      body: JSON.stringify({ brief_text }),
    }),
  dedupeJob: (brief_text: string, title = "") =>
    request<{
      similar: {
        requirement_id: string;
        production_title: string;
        similarity: number;
      }[];
    }>("/jobs/dedupe", {
      method: "POST",
      body: JSON.stringify({ brief_text, title }),
    }),
  confirmJob: (fields: Record<string, unknown>) =>
    request<Requirement>("/jobs/confirm", {
      method: "POST",
      body: JSON.stringify({ fields }),
    }),
  listBookings: () => request<Booking[]>("/bookings"),
  scheduleBookings: (requirementId?: string) =>
    request<Booking[]>(
      requirementId
        ? `/bookings/schedule?requirement_id=${encodeURIComponent(requirementId)}`
        : "/bookings/schedule"
    ),
  createBooking: (runId: string, talentId: string) =>
    request<Booking>("/bookings", {
      method: "POST",
      body: JSON.stringify({ run_id: runId, talent_id: talentId }),
    }),
  callsheetUrl: (bookingId: string) =>
    `${API_BASE}/export/callsheet/${bookingId}.pdf`,
  marketingDraft: (payload: {
    channel: "linkedin" | "newsletter";
    booking_id?: string;
    match_run_id?: string;
  }) =>
    request<MarketingDraft>("/marketing/draft", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listMarketingDrafts: () => request<MarketingDraft[]>("/marketing/drafts"),
  whatIf: (requirementId: string, params_override: Record<string, unknown>) =>
    request<WhatIfResult>("/what-if", {
      method: "POST",
      body: JSON.stringify({
        requirement_id: requirementId,
        scenario_label: "what-if",
        params_override,
      }),
    }),
  suggestWhatIf: (requirementId: string) =>
    request<{
      requirement_id: string;
      scenarios: {
        label: string;
        params_override: Record<string, unknown>;
        rationale: string;
      }[];
      provider?: string;
      used_llm?: boolean;
    }>(`/what-if/suggest?requirement_id=${encodeURIComponent(requirementId)}`, {
      method: "POST",
    }),
  explainMatch: (matchRunId: string, talentId: string) =>
    request<{
      match_run_id: string;
      talent_id: string;
      explanation: string;
      provider?: string;
      model?: string;
      cost_usd?: number;
      grounded?: boolean;
      used_llm?: boolean;
    }>("/matches/explain", {
      method: "POST",
      body: JSON.stringify({
        match_run_id: matchRunId,
        talent_id: talentId,
      }),
    }),
  talentSignals: (runId: string, talentId: string) =>
    request<{
      talent_id: string;
      match_run_id: string;
      no_show_risk: number;
      no_show_label: string;
      fair_weekly_rate_usd: number;
      rate_vs_fair: string | null;
      source: string;
    }>(`/matches/${runId}/signals/${talentId}`),
  aiCosts: () =>
    request<{
      call_count: number;
      total_cost_usd: number;
      by_provider: Record<string, number>;
      by_tier: Record<string, number>;
      recent: Record<string, unknown>[];
    }>("/ai/costs"),
  poolNarrative: (month = "2026-10") =>
    request<{
      narrative: string;
      provider?: string;
      used_llm?: boolean;
    }>(`/analytics/pool/narrative?month=${encodeURIComponent(month)}`, {
      method: "POST",
    }),
  analytics: () => request<PoolAnalytics>("/analytics/pool"),
  audit: (runId: string) => request<AuditEvent[]>(`/audit/${runId}`),
  edges: () => request<EdgeScenario[]>("/edges"),
  runEdge: (id: string) =>
    request<{
      passed: boolean;
      edge: EdgeScenario;
      result?: unknown;
      shortlist?: string[];
    }>(`/edges/${id}/run`, { method: "POST" }),
  copilot: (
    message: string,
    ctx?: Record<string, string | undefined>
  ) =>
    request<{
      reply: string;
      sources: string[];
      provider?: string;
      model?: string;
      tier?: string;
      cost_usd?: number;
    }>("/copilot/chat", {
      method: "POST",
      body: JSON.stringify({ message, ...ctx }),
    }),
  generateReport: (
    period_start: string,
    period_end: string,
    include_narrative = false
  ) =>
    request<ExecutiveReport>("/reports/executive", {
      method: "POST",
      body: JSON.stringify({
        period_start,
        period_end,
        include_narrative,
      }),
    }),
  narrateReport: (id: string) =>
    request<{
      narrative: string;
      provider?: string;
      used_llm?: boolean;
    }>(`/reports/${id}/narrate`, { method: "POST" }),
  listReports: () => request<ExecutiveReport[]>("/reports"),
  getReport: (id: string) => request<ExecutiveReport>(`/reports/${id}`),
  reportExportUrl: (id: string, ext: "pdf" | "xlsx") =>
    `${API_BASE}/reports/${id}.${ext}`,
  stagelyncSync: () =>
    request<{ synced: number; total: number; message: string }>(
      "/stagelync/sync",
      { method: "POST" }
    ),
  stagelyncPeople: () => request<StageLyncPerson[]>("/stagelync/people"),
  stagelyncDiscover: (q: string) =>
    request<StageLyncPerson[]>(
      `/stagelync/discover?q=${encodeURIComponent(q)}&limit=20`
    ),
  stagelyncImport: (id: string) =>
    request<{
      stagelync_person_id: string;
      talent_id: string;
      status: string;
      created: boolean;
    }>(`/stagelync/import/${id}`, { method: "POST" }),
  exportUrl: (
    runId: string,
    ext: "csv" | "json" | "xlsx" | "pdf" | "stagelync"
  ) => {
    if (ext === "stagelync")
      return `${API_BASE}/export/stagelync/${runId}.json`;
    return `${API_BASE}/export/shortlist/${runId}.${ext}`;
  },
};
