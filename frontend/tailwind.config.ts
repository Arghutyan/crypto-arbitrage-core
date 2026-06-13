import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark, professional trading-desk palette.
        base: {
          900: "#0a0e17",
          850: "#0d121d",
          800: "#111827",
          750: "#161f30",
          700: "#1c2638",
        },
        accent: {
          DEFAULT: "#5b8cff",
          muted: "#3b5bdb",
        },
        positive: "#22c55e",
        negative: "#ef4444",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(91,140,255,0.15), 0 8px 30px rgba(0,0,0,0.4)",
      },
    },
  },
  plugins: [],
};

export default config;
