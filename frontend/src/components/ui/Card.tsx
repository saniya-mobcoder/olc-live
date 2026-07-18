import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Adds a vibrant gradient top edge — for hero/feature cards. */
  accent?: boolean;
  interactive?: boolean;
}

export function Card({ accent, interactive, className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "relative rounded-2xl glass shadow-card overflow-hidden",
        interactive &&
          "transition-all duration-300 ease-premium hover:-translate-y-1 hover:shadow-glow-violet hover:border-white/20",
        className,
      )}
      {...props}
    >
      {accent && <span className="absolute inset-x-0 top-0 h-[3px] bg-spotlight" />}
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  eyebrow,
  subtitle,
  action,
  className,
}: {
  title: ReactNode;
  eyebrow?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-4 px-6 pt-5 pb-4", className)}>
      <div className="min-w-0">
        {eyebrow && (
          <div className="text-[11px] font-semibold uppercase tracking-eyebrow text-cyan mb-1.5">
            {eyebrow}
          </div>
        )}
        <h3 className="text-lg leading-tight">{title}</h3>
        {subtitle && <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function CardBody({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-6 pb-6", className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-6 py-4 border-t border-line bg-white/[0.02]", className)} {...props}>
      {children}
    </div>
  );
}
