import type { ReactNode } from "react";

/** Spotlight mark — a stage-light beam, self-contained SVG on a gradient tile. */
export function Logo({ size = 38 }: { size?: number }) {
  return (
    <span
      className="relative inline-flex items-center justify-center rounded-xl bg-spotlight shadow-glow-violet"
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg width={size * 0.6} height={size * 0.6} viewBox="0 0 24 24" fill="none">
        <path d="M12 3.2 15 9.5 9 9.5Z" fill="white" opacity="0.95" />
        <path d="M9.4 9.5h5.2l2.9 10.8a1 1 0 0 1-.97 1.3H7.47a1 1 0 0 1-.97-1.3Z" fill="white" opacity="0.28" />
        <circle cx="12" cy="6.4" r="1.2" fill="white" />
      </svg>
    </span>
  );
}

/** Full lockup: mark + Spotlight wordmark + parent brand line. */
export function Wordmark({ tagline = "by OLC" }: { tagline?: string }) {
  return (
    <div className="flex items-center gap-3">
      <Logo />
      <div className="leading-tight">
        <div className="font-display text-[17px] font-bold tracking-wide">
          <span className="text-gradient">SPOTLIGHT</span>
        </div>
        <div className="text-[10.5px] uppercase tracking-eyebrow text-ink-muted">{tagline}</div>
      </div>
    </div>
  );
}

/** App top bar — glass on midnight. */
export function AppHeader({ nav, actions }: { nav?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-[#070824]/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-6">
        <Wordmark />
        {nav && <div className="hidden md:flex">{nav}</div>}
        <div className="flex items-center gap-3">{actions}</div>
      </div>
    </header>
  );
}

/** Minimal footer. */
export function Footer() {
  return (
    <footer className="mt-20 border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-sm text-ink-muted sm:flex-row">
        <Wordmark tagline="Cast the impossible." />
        <span className="text-xs">© 2026 Our Legacy Creations · Entertainment Excellence, Worldwide</span>
      </div>
    </footer>
  );
}
