import Link from "next/link";
import { listCases, globalStats, type CaseRow } from "@/lib/queries";
import { Stat, VERDICT_META } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function Home() {
  const [cases, stats] = await Promise.all([listCases(), globalStats()]);

  return (
    <div className="space-y-10">
      <section className="animate-fade-up">
        <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand/30 bg-brand/10 px-3 py-1 text-xs text-brand-glow">
          Chain-of-custody for AI investigations
        </p>
        <h1 className="max-w-3xl text-3xl font-semibold leading-tight tracking-tight text-white md:text-[2.6rem]">
          Every finding traces to proof.{" "}
          <span className="text-brand">The AI never gets the final word.</span>
        </h1>
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-haze">
          An autonomous agent investigates digital evidence end to end - but deterministic
          code, not the model, decides what is <em>confirmed</em>, and every claim traces by
          foreign key to the exact tool record that proved it. When the model over-calls a
          threat, Veritas overrules it and shows you the gate that withheld promotion.
        </p>

        <div className="mt-7 grid grid-cols-2 gap-3 md:grid-cols-5">
          <Stat label="Cases" value={stats?.cases ?? 0} />
          <Stat label="Typed facts" value={(stats?.facts ?? 0).toLocaleString()} />
          <Stat label="Findings" value={stats?.findings ?? 0} />
          <Stat label="AI overruled by code" value={stats?.overruled ?? 0} accent />
          <Stat label="Forensic tools" value={stats?.tools ?? 0} />
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between">
          <h2 className="text-lg font-semibold text-white">Cases</h2>
          <Link href="/pivot" className="text-sm text-brand link-ghost hover:!text-brand-glow">
            Cross-case IOC pivot →
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {cases.map((c) => <CaseCard key={c.case_id} c={c} />)}
        </div>
      </section>
    </div>
  );
}

function CaseCard({ c }: { c: CaseRow }) {
  const v = VERDICT_META[c.verdict ?? "SUSPICIOUS"] ?? VERDICT_META.SUSPICIOUS;
  return (
    <Link
      href={`/case/${c.case_id}`}
      className={`panel group block p-5 transition hover:border-brand/40 ${v.glow}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="text-base font-semibold text-white">{c.case_name}</div>
          <div className="mt-0.5 text-xs text-haze mono">{c.sample_name}</div>
        </div>
        <span className={`rounded-md border px-2.5 py-1 text-xs font-semibold ${v.text} ${v.ring}`}>
          {c.verdict ?? "-"}
        </span>
      </div>
      <div className="mt-4 grid grid-cols-4 gap-2 text-center">
        <Mini label="Findings" value={c.finding_count} />
        <Mini label="Confirmed" value={c.confirmed_count} tone="text-confirmed" />
        <Mini label="Overruled" value={c.overruled_count} tone="text-brand" />
        <Mini label="Facts" value={c.fact_count} />
      </div>
      <div className="mt-4 text-xs text-haze opacity-0 transition group-hover:opacity-100">
        Open investigation →
      </div>
    </Link>
  );
}

function Mini({ label, value, tone = "text-white" }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-lg border border-line bg-ink-900/60 py-2">
      <div className={`text-lg font-semibold tabular-nums ${tone}`}>{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-haze">{label}</div>
    </div>
  );
}
