import { forwardRef } from "react";
import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
  ReactNode,
} from "react";
import { cn } from "@/lib/cn";

const control =
  "w-full rounded-xl border border-line-strong bg-white/[0.04] px-3.5 text-sm text-ink " +
  "placeholder:text-ink-muted transition-colors duration-150 backdrop-blur " +
  "focus:border-cyan focus:outline-none focus:bg-white/[0.07]";

export function Label({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="block text-[11px] font-semibold uppercase tracking-eyebrow text-ink-muted mb-1.5">
      {children}
    </label>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => <input ref={ref} className={cn(control, "h-10", className)} {...props} />,
);
Input.displayName = "Input";

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <select ref={ref} className={cn(control, "h-10 pr-8 appearance-none cursor-pointer [&>option]:text-ink [&>option]:bg-[#14163f]", className)} {...props}>
      {children}
    </select>
  ),
);
Select.displayName = "Select";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => <textarea ref={ref} className={cn(control, "py-2.5 min-h-[96px] resize-y", className)} {...props} />,
);
Textarea.displayName = "Textarea";

export function Field({
  label,
  hint,
  htmlFor,
  children,
}: {
  label?: string;
  hint?: string;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <div>
      {label && <Label htmlFor={htmlFor}>{label}</Label>}
      {children}
      {hint && <p className="mt-1 text-xs text-ink-muted">{hint}</p>}
    </div>
  );
}
