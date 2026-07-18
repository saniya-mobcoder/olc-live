import { cn } from "@/lib/cn";

/** Color band for a 0–100 match score (neon on dark), consistent everywhere. */
export function scoreBand(score: number): { stroke: string; text: string; label: string } {
  if (score >= 85) return { stroke: "var(--lime)", text: "text-success-fg", label: "Excellent" };
  if (score >= 70) return { stroke: "var(--cyan)", text: "text-info-fg", label: "Good" };
  if (score >= 50) return { stroke: "var(--amber)", text: "text-warning-fg", label: "Partial" };
  return { stroke: "var(--danger)", text: "text-danger-fg", label: "Weak" };
}

/** Circular score dial (SVG, no deps). */
export function ScoreRing({
  score,
  size = 72,
  stroke = 7,
  showLabel = true,
}: {
  score: number;
  size?: number;
  stroke?: number;
  showLabel?: boolean;
}) {
  const clamped = Math.max(0, Math.min(100, score));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const band = scoreBand(clamped);
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={band.stroke}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - clamped / 100)}
          style={{ transition: "stroke-dashoffset 0.9s cubic-bezier(0.22,1,0.36,1)", filter: "drop-shadow(0 0 6px " + band.stroke + ")" }}
        />
      </svg>
      {showLabel && <span className="absolute font-display text-lg text-ink">{Math.round(clamped)}</span>}
    </div>
  );
}

/** Horizontal score bar with band coloring + optional caption. */
export function ScoreBar({
  score,
  label,
  className,
}: {
  score: number;
  label?: string;
  className?: string;
}) {
  const clamped = Math.max(0, Math.min(100, score));
  const band = scoreBand(clamped);
  return (
    <div className={cn("w-full", className)}>
      {label && (
        <div className="flex justify-between text-xs mb-1">
          <span className="text-ink-muted">{label}</span>
          <span className={cn("font-semibold", band.text)}>{Math.round(clamped)}</span>
        </div>
      )}
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${clamped}%`,
            background: band.stroke,
            boxShadow: "0 0 10px " + band.stroke,
            transition: "width 0.9s cubic-bezier(0.22,1,0.36,1)",
          }}
        />
      </div>
    </div>
  );
}
