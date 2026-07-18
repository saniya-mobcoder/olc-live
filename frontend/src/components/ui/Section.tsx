import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/** Uppercase vibrant eyebrow label. */
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("text-[11px] font-bold uppercase tracking-eyebrow text-cyan", className)}>
      {children}
    </div>
  );
}

/** Section heading with optional eyebrow, subtitle and right-aligned action. */
export function SectionHeader({
  eyebrow,
  title,
  subtitle,
  action,
  className,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-end justify-between gap-4 mb-6", className)}>
      <div>
        {eyebrow && <Eyebrow className="mb-2">{eyebrow}</Eyebrow>}
        <h2 className="text-2xl leading-tight">{title}</h2>
        {subtitle && <p className="mt-2 text-sm text-ink-muted max-w-2xl">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

/** Skill / tag chip. */
export function Chip({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-lg border border-line bg-white/5 px-2.5 py-1 text-xs font-medium text-ink-soft",
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Thin divider. */
export function Divider({ className }: { className?: string }) {
  return <hr className={cn("border-0 border-t border-line", className)} />;
}
