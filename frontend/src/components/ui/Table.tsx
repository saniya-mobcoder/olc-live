import type { HTMLAttributes, ThHTMLAttributes, TdHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/** Premium data table primitives (vibrant dark). */
export function TableWrap({ className, children }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("rounded-2xl glass shadow-card overflow-hidden", className)}>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
    </div>
  );
}

export function THead({ children }: HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead className="bg-white/[0.04]">
      <tr>{children}</tr>
    </thead>
  );
}

export function TH({ className, children, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn("text-left font-semibold text-[11px] uppercase tracking-eyebrow text-ink-muted px-4 py-3 whitespace-nowrap", className)}
      {...props}
    >
      {children}
    </th>
  );
}

export function TR({ className, children, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr className={cn("border-t border-line transition-colors hover:bg-white/[0.04]", className)} {...props}>
      {children}
    </tr>
  );
}

export function TD({ className, children, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("px-4 py-3 text-ink-soft align-middle", className)} {...props}>
      {children}
    </td>
  );
}
