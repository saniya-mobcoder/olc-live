import { cn } from "@/lib/cn";

export interface TabItem<T extends string = string> {
  id: T;
  label: string;
}

/** Pill tab bar — vibrant gradient active state. */
export function Tabs<T extends string>({
  items,
  value,
  onChange,
  className,
}: {
  items: TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  className?: string;
}) {
  return (
    <div className={cn("inline-flex flex-wrap gap-1 rounded-full glass p-1", className)}>
      {items.map((t) => {
        const active = t.id === value;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={cn(
              "rounded-full px-4 py-1.5 text-sm font-semibold transition-all duration-200 ease-premium",
              active
                ? "bg-spotlight text-white shadow-glow-violet"
                : "text-ink-muted hover:text-ink hover:bg-white/5",
            )}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
