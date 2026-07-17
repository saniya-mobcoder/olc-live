"use client";

import dynamic from "next/dynamic";
import type { MatchResult, Requirement } from "@/lib/types";
import { BreakdownBars, ScoreRadar } from "./ScoreVisuals";

const TalentMap = dynamic(() => import("./TalentMap").then((m) => m.TalentMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-72 items-center justify-center border border-[var(--olc-ink)]/10 text-sm">
      Loading map…
    </div>
  ),
});

export function ShortlistPanel({
  requirement,
  shortlist,
  selectedId,
  onSelect,
  onDecision,
  decisions,
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
}) {
  const selected = shortlist.find((r) => r.talent_id === selectedId) || shortlist[0];

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <div className="space-y-3">
        {shortlist.map((row, i) => {
          const t = row.talent;
          const active = (selected?.talent_id || "") === row.talent_id;
          const prior = row.breakdown?.feedback_prior;
          const hybridMode = row.breakdown?.ranking_mode === "hybrid";
          const decided = decisions?.[row.talent_id];
          return (
            <div
              key={row.talent_id}
              className={`animate-rise border px-4 py-4 transition ${
                active
                  ? "border-[var(--olc-forest)] bg-[var(--olc-mint)]/60"
                  : "border-[var(--olc-ink)]/10 bg-white/50 hover:border-[var(--olc-leaf)]"
              }`}
              style={{ animationDelay: `${i * 0.06}s` }}
            >
              <button
                type="button"
                onClick={() => onSelect(row.talent_id)}
                className="w-full text-left"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-[var(--olc-leaf)]">
                      Rank {row.rank} · {row.talent_id}
                      {hybridMode && prior != null
                        ? ` · feedback boost ${prior.toFixed(0)}`
                        : ""}
                    </p>
                    <h3 className="mt-1 text-xl text-[var(--olc-ink)]">
                      {t?.full_name}
                    </h3>
                    <p className="mt-1 text-sm text-[var(--olc-ink)]/70">
                      {t?.primary_role}
                      {row.breakdown?.via_secondary_role
                        ? " · via secondary role"
                        : ""}
                      {" · "}
                      {t?.city}, {t?.country}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-3xl font-medium tabular-nums text-[var(--olc-forest)]">
                      {row.score?.toFixed(1)}
                    </p>
                    <p className="text-xs uppercase tracking-wide">
                      {row.match_category}
                    </p>
                    {decided ? (
                      <p className="mt-1 text-xs uppercase tracking-wide text-[var(--olc-forest)]">
                        {decided}
                      </p>
                    ) : null}
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {row.positive_reasons.slice(0, 2).map((reason) => (
                    <span key={reason} className="badge badge-ready">
                      {reason}
                    </span>
                  ))}
                  {row.risk_factors.map((f) => (
                    <span key={f} className="badge badge-risk">
                      {f}
                    </span>
                  ))}
                  {hybridMode ? (
                    <span className="badge badge-ready">AI-assisted rank</span>
                  ) : null}
                </div>
              </button>
              {onDecision ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {(
                    [
                      ["hire", "Hire"],
                      ["hold", "Hold"],
                      ["reject", "Pass"],
                    ] as const
                  ).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => onDecision(row.talent_id, value)}
                      className={`border px-3 py-1 text-xs uppercase tracking-wider ${
                        decided === value
                          ? "border-[var(--olc-forest)] bg-[var(--olc-mint)]/70"
                          : "border-[var(--olc-ink)]/20 bg-white/80 hover:border-[var(--olc-forest)]"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="panel space-y-5 p-5">
        {selected ? (
          <>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--olc-leaf)]">
                Score anatomy
              </p>
              <h3 className="mt-1 text-2xl">{selected.talent?.full_name}</h3>
              <p className="text-sm text-[var(--olc-ink)]/65">
                Audition {selected.talent?.audition_readiness_score} · Credits{" "}
                {selected.talent?.average_director_rating}/5 (
                {selected.talent?.completed_productions}) · {selected.distance_km} km
                from set
              </p>
              {selected.breakdown?.feedback_prior != null ? (
                <p className="mt-1 text-xs text-[var(--olc-ink)]/55">
                  Feedback prior {selected.breakdown.feedback_prior.toFixed(1)}
                  {selected.breakdown.hybrid_score != null
                    ? ` · hybrid sort ${selected.breakdown.hybrid_score.toFixed(1)}`
                    : ""}
                </p>
              ) : null}
            </div>
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-[var(--olc-ink)]/55">
                Audition readiness
              </p>
              <div className="score-bar h-2">
                <span
                  style={{
                    width: `${Math.min(100, selected.talent?.audition_readiness_score || 0)}%`,
                  }}
                />
              </div>
            </div>
            <BreakdownBars result={selected} />
            <ScoreRadar result={selected} />
            <TalentMap requirement={requirement} shortlist={shortlist} />
          </>
        ) : (
          <p className="text-sm">Run a match to see score visuals.</p>
        )}
      </div>
    </div>
  );
}
