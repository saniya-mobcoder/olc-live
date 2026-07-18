"use client";

import dynamic from "next/dynamic";
import type { MatchResult, Requirement } from "@/lib/types";
import {
  Badge,
  Button,
  Chip,
  ScoreBar,
  ScoreRing,
  StatusBadge,
} from "@/components/ui";
import { BreakdownBars, ScoreRadar } from "./ScoreVisuals";

const TalentMap = dynamic(() => import("./TalentMap").then((m) => m.TalentMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-56 items-center justify-center rounded-xl border border-line text-sm text-ink-muted">
      Loading map…
    </div>
  ),
});

function initials(name?: string | null) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "?";
}

export function ShortlistPanel({
  requirement,
  shortlist,
  selectedId,
  onSelect,
  onDecision,
  decisions,
  onExplain,
  explanations,
  compact = false,
}: {
  requirement: Requirement;
  shortlist: MatchResult[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDecision?: (
    talentId: string,
    decision: "hire" | "hold" | "reject"
  ) => void;
  decisions?: Record<string, string>;
  onExplain?: (talentId: string) => void;
  explanations?: Record<string, string>;
  compact?: boolean;
}) {
  const selected =
    shortlist.find((r) => r.talent_id === selectedId) || shortlist[0];

  const list = (
    <div className="space-y-3">
      {shortlist.map((row, i) => {
        const t = row.talent;
        const active = (selected?.talent_id || "") === row.talent_id;
        const prior = row.breakdown?.feedback_prior;
        const hybridMode = row.breakdown?.ranking_mode === "hybrid";
        const decided = decisions?.[row.talent_id];
        const ml = row.breakdown?.ml_signals;
        const skills = (t?.primary_skills || []).slice(0, 3);
        return (
          <div
            key={row.talent_id}
            className={`animate-rise rounded-2xl border p-4 transition ${
              active
                ? "border-cyan/40 bg-white/[0.08] shadow-glow-cyan"
                : "border-line bg-white/[0.03] hover:border-line-strong hover:bg-white/[0.05]"
            }`}
            style={{ animationDelay: `${i * 0.05}s` }}
          >
            <button
              type="button"
              onClick={() => onSelect(row.talent_id)}
              className="w-full text-left"
            >
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-spotlight text-sm font-bold text-white shadow-glow-violet">
                  {initials(t?.full_name)}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-semibold uppercase tracking-eyebrow text-ink-muted">
                    Rank {row.rank} · {row.talent_id}
                    {hybridMode && prior != null
                      ? ` · boost ${prior.toFixed(0)}`
                      : ""}
                  </p>
                  <h3 className="mt-0.5 truncate font-display text-lg text-ink">
                    {t?.full_name}
                  </h3>
                  <p className="mt-0.5 truncate text-sm text-ink-muted">
                    {t?.primary_role}
                    {row.breakdown?.via_secondary_role
                      ? " · via secondary"
                      : ""}
                    {" · "}
                    {t?.city}, {t?.country}
                  </p>
                </div>
                <ScoreRing score={row.score ?? 0} size={56} stroke={6} />
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <StatusBadge label={row.match_category || "Match"} />
                {skills.map((s) => (
                  <Chip key={s}>{s}</Chip>
                ))}
                {decided ? <Badge tone="success">{decided}</Badge> : null}
                {ml?.no_show_label ? (
                  <Badge
                    tone={ml.no_show_label === "high" ? "danger" : "success"}
                  >
                    no-show {ml.no_show_label}
                  </Badge>
                ) : null}
              </div>
            </button>
            <div className="mt-3 flex flex-wrap gap-2">
              {onExplain ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => onExplain(row.talent_id)}
                >
                  Explain
                </Button>
              ) : null}
              {onDecision
                ? (
                    [
                      ["hire", "Hire"],
                      ["hold", "Hold"],
                      ["reject", "Pass"],
                    ] as const
                  ).map(([value, label]) => (
                    <Button
                      key={value}
                      type="button"
                      size="sm"
                      variant={decided === value ? "primary" : "outline"}
                      onClick={() => onDecision(row.talent_id, value)}
                    >
                      {label}
                    </Button>
                  ))
                : null}
            </div>
            {explanations?.[row.talent_id] ? (
              <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                {explanations[row.talent_id]}
              </p>
            ) : null}
          </div>
        );
      })}
    </div>
  );

  if (compact) return list;

  return (
    <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
      {list}
      <div className="card-surface space-y-5 p-5">
        {selected ? (
          <>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-ink-muted">
                Score anatomy
              </p>
              <h3 className="mt-1 font-display text-2xl text-ink">
                {selected.talent?.full_name}
              </h3>
              <p className="mt-1 text-sm text-ink-muted">
                Audition {selected.talent?.audition_readiness_score} · Credits{" "}
                {selected.talent?.average_director_rating}/5 (
                {selected.talent?.completed_productions}) ·{" "}
                {selected.distance_km} km
              </p>
              {selected.breakdown?.rerank_reason ? (
                <p className="mt-2 text-xs text-ink-muted">
                  {selected.breakdown.rerank_reason}
                </p>
              ) : null}
            </div>
            <ScoreBar
              label="Audition readiness"
              score={selected.talent?.audition_readiness_score || 0}
            />
            <BreakdownBars result={selected} />
            <ScoreRadar result={selected} />
            <TalentMap requirement={requirement} shortlist={shortlist} />
          </>
        ) : (
          <p className="text-sm text-ink-muted">
            Run a match to see score visuals.
          </p>
        )}
      </div>
    </div>
  );
}

export function TalentDetailPane({
  requirement,
  shortlist,
  selected,
}: {
  requirement: Requirement;
  shortlist: MatchResult[];
  selected: MatchResult | null;
}) {
  if (!selected) {
    return (
      <div className="card-surface flex h-full min-h-[20rem] items-center justify-center p-8 text-sm text-ink-muted">
        Select a shortlisted talent to inspect scores and map.
      </div>
    );
  }
  return (
    <div className="card-surface space-y-5 p-5">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-ink-muted">
          Score anatomy
        </p>
        <h3 className="mt-1 font-display text-2xl text-ink">
          {selected.talent?.full_name}
        </h3>
        <p className="mt-1 text-sm text-ink-muted">
          Audition {selected.talent?.audition_readiness_score} · Credits{" "}
          {selected.talent?.average_director_rating}/5 (
          {selected.talent?.completed_productions}) · {selected.distance_km} km
        </p>
        {selected.breakdown?.rerank_reason ? (
          <p className="mt-2 text-xs text-ink-muted">
            {selected.breakdown.rerank_reason}
          </p>
        ) : null}
      </div>
      <ScoreBar
        label="Audition readiness"
        score={selected.talent?.audition_readiness_score || 0}
      />
      <BreakdownBars result={selected} />
      <ScoreRadar result={selected} />
      <TalentMap requirement={requirement} shortlist={shortlist} />
    </div>
  );
}
