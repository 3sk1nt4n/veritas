import Link from "next/link";
import type { ReactNode } from "react";

// ---- verdict / disposition semantics (literal classes so Tailwind keeps them) ----
export const BUCKET_META: Record<
  string,
  { label: string; text: string; bg: string; border: string; dot: string }
> = {
  confirmed_malicious_atomic: { label: "Confirmed malicious", text: "text-confirmed", bg: "bg-confirmed/10", border: "border-confirmed/30", dot: "bg-confirmed" },
  suspicious_needs_review:    { label: "Suspicious",          text: "text-suspicious", bg: "bg-suspicious/10", border: "border-suspicious/30", dot: "bg-suspicious" },
  benign_or_false_positive:   { label: "Benign / FP",         text: "text-benign", bg: "bg-benign/10", border: "border-benign/30", dot: "bg-benign" },
  inconclusive_unresolved:    { label: "Inconclusive",        text: "text-inconclusive", bg: "bg-inconclusive/10", border: "border-inconclusive/30", dot: "bg-inconclusive" },
  synthesis_narrative:        { label: "Synthesis",           text: "text-synthesis", bg: "bg-synthesis/10", border: "border-synthesis/30", dot: "bg-synthesis" },
};

export const SEVERITY_META: Record<string, { text: string; dot: string }> = {
  CRITICAL: { text: "text-confirmed", dot: "bg-confirmed" },
  HIGH:     { text: "text-suspicious", dot: "bg-suspicious" },
  MEDIUM:   { text: "text-amber-300", dot: "bg-amber-300" },
  LOW:      { text: "text-haze", dot: "bg-inconclusive" },
  INFO:     { text: "text-haze", dot: "bg-inconclusive" },
};

export const VERDICT_META: Record<string, { text: string; ring: string; glow: string }> = {
  CONFIRMED:  { text: "text-confirmed", ring: "border-confirmed/40", glow: "shadow-[0_0_60px_-15px_rgba(244,63,94,0.5)]" },
  SUSPICIOUS: { text: "text-suspicious", ring: "border-suspicious/40", glow: "shadow-[0_0_60px_-15px_rgba(245,158,11,0.45)]" },
  CLEAN:      { text: "text-benign", ring: "border-benign/40", glow: "shadow-[0_0_60px_-15px_rgba(16,185,129,0.45)]" },
};

export function Pill({ bucket, count }: { bucket: string; count?: number }) {
  const m = BUCKET_META[bucket] ?? BUCKET_META.inconclusive_unresolved;
  return (
    <span className={`chip ${m.bg} ${m.border} ${m.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
      {m.label}
      {count != null && <span className="ml-1 font-semibold tabular-nums">{count}</span>}
    </span>
  );
}

export function Severity({ level }: { level: string | null }) {
  if (!level) return null;
  const m = SEVERITY_META[level] ?? SEVERITY_META.INFO;
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${m.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
      {level}
    </span>
  );
}

export function Tool({ name }: { name: string }) {
  return <span className="chip mono !text-[11px] text-brand-glow border-brand/20 bg-brand/5">{name}</span>;
}

export function Mono({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <code className={`mono text-[12px] text-slate-300 ${className}`}>{children}</code>;
}

export function Stat({ label, value, accent = false }: { label: string; value: ReactNode; accent?: boolean }) {
  return (
    <div className="panel px-4 py-3">
      <div className={`stat-num ${accent ? "text-brand" : ""}`}>{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-haze">{label}</div>
    </div>
  );
}

export function Crumbs({ items }: { items: { href?: string; label: string }[] }) {
  return (
    <nav className="mb-5 flex items-center gap-2 text-sm text-haze">
      {items.map((it, i) => (
        <span key={i} className="flex items-center gap-2">
          {it.href ? <Link href={it.href} className="link-ghost">{it.label}</Link> : <span className="text-slate-300">{it.label}</span>}
          {i < items.length - 1 && <span className="text-line">/</span>}
        </span>
      ))}
    </nav>
  );
}

// entity kind -> short glyph for the pivot
export const ENTITY_GLYPH: Record<string, string> = {
  pid: "▣", ip: "◉", hash: "#", reg: "⌘", appcompatcache: "▷", handle: "⊞",
  file: "▤", url: "↗", service: "⚙", task: "⏱", user: "☻", event: "✦",
};
