import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#F7F9FC",
        foreground: "#101828",
        brand: { DEFAULT: "#2563EB", dark: "#1D4ED8" },
        muted: "#667085",
        border: "#E4E7EC",
        card: "#FFFFFF",
        navy: { DEFAULT: "#0B1220", light: "#111C2E" },
        success: { DEFAULT: "#12B76A", bg: "#ECFDF3", border: "#A6F4C5", text: "#067647" },
        danger: { DEFAULT: "#F04438", bg: "#FEF3F2", border: "#FECDCA", text: "#B42318" },
        warning: { DEFAULT: "#F79009", bg: "#FFFAEB", border: "#FEDF89", text: "#B54708" },
        info: { DEFAULT: "#2E90FA", bg: "#EFF8FF", border: "#B2DDFF", text: "#175CD3" },
        purple: { DEFAULT: "#7F56D9", bg: "#F4F3FF" }
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "SFMono-Regular", "Consolas", "monospace"]
      },
      borderRadius: { sm: "6px", md: "10px", lg: "14px", xl: "18px" },
      boxShadow: {
        low: "0 1px 2px rgba(16,24,40,0.04)",
        medium: "0 4px 12px rgba(16,24,40,0.08)",
        high: "0 12px 32px rgba(16,24,40,0.12)"
      }
    }
  },
  plugins: []
};

export default config;
