import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/** KPI / stat card — Pool analytics, Reports, dashboard headers. */
export function Stat({
  label,
  value,
  hint,
  delta,
  icon,
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  delta?: { value: string; positive?: boolean };
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("group relative rounded-2xl glass shadow-card p-5 flex flex-col gap-2 overflow-hidden", className)}>
      <span className="pointer-events-none absolute -right-8 -top-10 h-24 w-24 rounded-full bg-spotlight opacity-20 blur-2xl transition-opacity group-hover:opacity-40" />
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-eyebrow text-ink-muted">{label}</span>
        {icon && <span className="text-cyan">{icon}</span>}
      </div>
      <div className="font-display text-3xl leading-none text-ink">{value}</div>
      <div className="flex items-center gap-2">
        {delta && (
          <span className={cn("text-xs font-semibold", delta.positive === false ? "text-danger-fg" : "text-success-fg")}>
            {delta.positive === false ? "▼" : "▲"} {delta.value}
          </span>
        )}
        {hint && <span className="text-xs text-ink-muted">{hint}</span>}
      </div>
    </div>
  );
}
