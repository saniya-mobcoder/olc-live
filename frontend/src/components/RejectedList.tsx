"use client";

import { useState } from "react";
import type { MatchResult } from "@/lib/types";
import { Badge, Button } from "@/components/ui";

export function RejectedList({
  rejected,
  onExplain,
  explanations,
  defaultOpen = false,
}: {
  rejected: MatchResult[];
  onExplain?: (talentId: string) => void;
  explanations?: Record<string, string>;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  if (!rejected.length) return null;

  return (
    <div className="card-surface overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
      >
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-ink-muted">
            Hard gates
          </p>
          <p className="mt-0.5 font-display text-lg text-ink">
            {rejected.length} gated out
          </p>
        </div>
        <span className="text-sm text-ink-muted">{open ? "Hide" : "Show"}</span>
      </button>
      {open ? (
        <div className="space-y-3 border-t border-line px-5 pb-5 pt-3">
          {rejected.map((row) => (
            <div
              key={row.talent_id}
              className="rounded-xl border border-danger/25 bg-danger-bg/40 px-4 py-3"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h4 className="font-display text-base text-ink">
                  {row.talent?.full_name}{" "}
                  <span className="text-sm font-body text-ink-muted">
                    {row.talent_id}
                  </span>
                </h4>
                <div className="flex flex-wrap gap-1">
                  {row.failed_gates.map((g) => (
                    <Badge key={g} tone="danger">
                      {g}
                    </Badge>
                  ))}
                </div>
              </div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-soft">
                {row.rejection_reasons.map((r, i) => (
                  <li key={`${row.talent_id}-reason-${i}`}>{r}</li>
                ))}
              </ul>
              {onExplain ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="mt-2"
                  onClick={() => onExplain(row.talent_id)}
                >
                  Plain-English explain
                </Button>
              ) : null}
              {explanations?.[row.talent_id] ? (
                <p className="mt-2 text-sm text-ink-soft">
                  {explanations[row.talent_id]}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
