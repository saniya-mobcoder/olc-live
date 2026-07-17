"use client";

import type { MatchResult } from "@/lib/types";

export function RejectedList({ rejected }: { rejected: MatchResult[] }) {
  return (
    <div className="space-y-3">
      {rejected.map((row) => (
        <div
          key={row.talent_id}
          className="border border-[var(--olc-coral)]/25 bg-[#f8ebe6]/70 px-4 py-3"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h4 className="text-lg">
              {row.talent?.full_name}{" "}
              <span className="text-sm text-[var(--olc-ink)]/55">{row.talent_id}</span>
            </h4>
            <div className="flex flex-wrap gap-1">
              {row.failed_gates.map((g) => (
                <span key={g} className="badge badge-risk">
                  {g}
                </span>
              ))}
            </div>
          </div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--olc-ink)]/80">
            {row.rejection_reasons.map((r, i) => (
              <li key={`${row.talent_id}-reason-${i}`}>{r}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
