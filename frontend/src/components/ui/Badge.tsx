import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type Tone =
  | "neutral"
  | "navy"
  | "gold"
  | "success"
  | "warning"
  | "danger"
  | "info";

const tones: Record<Tone, string> = {
  neutral: "bg-white/5 text-ink-soft border-line-strong",
  navy: "bg-white/5 text-[#c7b6ff] border-violet",
  gold: "bg-white/5 text-warning-fg border-amber",
  success: "bg-success-bg text-success-fg border-success",
  warning: "bg-warning-bg text-warning-fg border-warning",
  danger: "bg-danger-bg text-danger-fg border-danger",
  info: "bg-info-bg text-info-fg border-info",
};

export function Badge({
  tone = "neutral",
  dot = false,
  children,
  className,
}: {
  tone?: Tone;
  dot?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide",
        tones[tone],
        className,
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

/** Map an OLC match_category → badge tone (consistent status colors). */
export function matchCategoryTone(category: string): Tone {
  const c = category.toLowerCase();
  if (c.includes("excellent")) return "success";
  if (c.includes("good")) return "info";
  if (c.includes("partial")) return "warning";
  if (c.includes("weak")) return "neutral";
  if (c.includes("not eligible") || c.includes("rejection")) return "danger";
  return "neutral";
}

export function StatusBadge({ label, className }: { label: string; className?: string }) {
  return (
    <Badge tone={matchCategoryTone(label)} dot className={className}>
      {label}
    </Badge>
  );
}
