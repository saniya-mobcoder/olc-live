import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "gold" | "outline" | "ghost" | "subtle" | "danger";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 font-semibold rounded-full " +
  "transition-all duration-200 ease-premium select-none whitespace-nowrap " +
  "disabled:opacity-50 disabled:pointer-events-none active:translate-y-px";

const variants: Record<Variant, string> = {
  // Signature spotlight gradient with glow
  primary:
    "bg-spotlight text-white shadow-glow-violet hover:brightness-110 hover:shadow-glow-magenta",
  // Warm gradient accent
  gold:
    "bg-warm text-[#2a1206] shadow-[0_10px_40px_-8px_rgba(255,176,32,0.55)] hover:brightness-105",
  // Glass outline
  outline:
    "border border-line-strong text-ink bg-white/5 hover:bg-white/10 backdrop-blur",
  ghost:
    "text-ink-soft hover:text-ink hover:bg-white/5",
  subtle:
    "bg-white/[0.06] text-ink hover:bg-white/[0.12] border border-line",
  danger:
    "bg-danger text-white hover:brightness-110",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-4 text-[13px]",
  md: "h-10 px-5 text-sm",
  lg: "h-12 px-7 text-[15px]",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", leftIcon, rightIcon, className, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(base, variants[variant], sizes[size], className)}
      {...props}
    >
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  ),
);
Button.displayName = "Button";
