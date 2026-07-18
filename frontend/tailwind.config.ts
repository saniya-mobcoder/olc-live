import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--bg)",
        foreground: "var(--ink)",

        bg: {
          DEFAULT: "var(--bg)",
          2: "var(--bg-2)",
        },
        surface: {
          DEFAULT: "var(--surface)",
          solid: "var(--surface-solid)",
          muted: "var(--surface-muted)",
        },
        ink: {
          DEFAULT: "var(--ink)",
          soft: "var(--ink-soft)",
          muted: "var(--ink-muted)",
        },
        line: {
          DEFAULT: "var(--line)",
          strong: "var(--line-strong)",
        },

        // Vibrant stage lights
        magenta: "var(--magenta)",
        violet: "var(--violet)",
        cyan: "var(--cyan)",
        amber: "var(--amber)",
        coral: "var(--coral)",
        lime: "var(--lime)",

        // Semantic status
        success: { DEFAULT: "var(--success)", bg: "var(--success-bg)", fg: "var(--success-fg)" },
        warning: { DEFAULT: "var(--warning)", bg: "var(--warning-bg)", fg: "var(--warning-fg)" },
        danger: { DEFAULT: "var(--danger)", bg: "var(--danger-bg)", fg: "var(--danger-fg)" },
        info: { DEFAULT: "var(--info)", bg: "var(--info-bg)", fg: "var(--info-fg)" },
      },
      backgroundImage: {
        spotlight: "var(--grad-spotlight)",
        warm: "var(--grad-warm)",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        lg: "14px",
        xl: "18px",
        "2xl": "22px",
        "3xl": "30px",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        elevated: "var(--shadow-elevated)",
        "glow-magenta": "var(--glow-magenta)",
        "glow-violet": "var(--glow-violet)",
        "glow-cyan": "var(--glow-cyan)",
      },
      letterSpacing: {
        eyebrow: "0.20em",
      },
      transitionTimingFunction: {
        premium: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
} satisfies Config;
