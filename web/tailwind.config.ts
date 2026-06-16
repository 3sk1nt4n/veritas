import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // investigation-console palette
        ink: {
          950: "#070a10",
          900: "#0b0f17",
          850: "#0f1623",
          800: "#141d2b",
          700: "#1c2740",
          600: "#26324f",
        },
        line: "#1e2a40",
        haze: "#8597b3",
        brand: { DEFAULT: "#22d3ee", dim: "#0e7490", glow: "#67e8f9" },
        // verdict semantics
        confirmed: "#f43f5e",
        suspicious: "#f59e0b",
        benign: "#10b981",
        inconclusive: "#64748b",
        synthesis: "#a78bfa",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34,211,238,0.25), 0 8px 40px -12px rgba(34,211,238,0.25)",
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 12px 40px -20px rgba(0,0,0,0.8)",
      },
      keyframes: {
        "fade-up": { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        "draw": { from: { strokeDashoffset: "1" }, to: { strokeDashoffset: "0" } },
      },
      animation: { "fade-up": "fade-up .4s ease both" },
    },
  },
  plugins: [],
};
export default config;
