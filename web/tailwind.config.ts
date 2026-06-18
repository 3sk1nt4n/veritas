import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // investigation-console palette - VulnPilot identity on a dark base:
        // orange brand + slate structure (their light theme adapted to dark).
        ink: {
          950: "#070a10",
          900: "#0b0f17",
          850: "#0f1623",
          800: "#141d2b",
          700: "#1c2740",
          600: "#26324f",
        },
        line: "#1e2a40",
        haze: "#94a3b8", // VulnPilot --muted slate
        // VulnPilot signature: orange (#ea580c / #f97316), lifted for a dark UI
        brand: { DEFAULT: "#f97316", dim: "#ea580c", glow: "#fdba74" },
        // VulnPilot secondary accent: teal (their "--cyan")
        teal: { DEFAULT: "#0d9488", glow: "#2dd4bf" },
        // verdict semantics, aligned to VulnPilot's exact severity shades
        confirmed: "#ef4444", // VulnPilot --crit
        suspicious: "#f59e0b", // VulnPilot --amber
        benign: "#16a34a", // VulnPilot --low
        inconclusive: "#64748b", // VulnPilot --muted / --info
        synthesis: "#8b5cf6", // VulnPilot --purple
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(249,115,22,0.25), 0 8px 40px -12px rgba(249,115,22,0.25)",
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
