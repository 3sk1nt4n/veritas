import Link from "next/link";
import { notFound } from "next/navigation";
import { getCase, getScoreboard, getEvidence, getOverruled, listFindings } from "@/lib/queries";
import { Crumbs, VERDICT_META, Severity, Pill } from "@/components/ui";
import { Scoreboard } from "@/components/Scoreboard";

export const dynamic = "force-dynamic";

export default async function CaseDashboard({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  const c = await getCase(caseId);
  if (!c) notFound();

  const [counts, evidence, overruled, confirmed] = await Promise.all([
    getScoreboard(caseId),
    getEvidence(caseId),
    getOverruled(caseId),
    listFindings(caseId, "confirmed_malicious_atomic"),
  ]);

  const v = VERDICT_META[c.verdict ?? "SUSPICIOUS"] ?? VERDICT_META.SUSPICIOUS;
  const ev = evidence[0];

  return (
    <div className="space-y-7">
      <Crumbs items={[{ href: "/", label: "Cases" }, { label: c.case_name }]} />

      {/* verdict banner */}
      <section className={`panel flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between ${v.glow}`}>
        <div>
          <div className="text-xs uppercase tracking-wide text-haze">Case verdict</div>
          <div className={`mt-1 text-4xl font-bold tracking-tight ${v.text}`}>{c.verdict ?? "—"}</div>
          <div className="mt-2 text-sm text-white">{c.case_name}</div>
          <div className="text-xs text-haze mono">{c.sample_name}</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {ev && (
            <span className={`chip ${ev.evidence_unmodified ? "border-benign/30 bg-benign/10 text-benign" : "border-suspicious/30 bg-suspicious/10 text-suspicious"}`}>
              {ev.evidence_unmodified ? "✓ Evidence unmodified" : "⚠ Integrity unverified"}
            </span>
          )}
          <span className="chip">{c.fact_count.toLocaleString()} typed facts</span>
          {c.model_used && <span className="chip mono">{c.model_used}</span>}
        </div>
      </section>

      {/* the overrule highlight — the product's headline */}
      {overruled.length > 0 && (
        <Link href={`/case/${caseId}/findings?bucket=suspicious_needs_review`}
          className="panel block border-brand/30 bg-brand/[0.06] p-5 transition hover:border-brand/50">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-brand/40 bg-brand/10 text-brand">⚖</span>
            <div>
              <div className="text-sm font-semibold text-white">
                The AI was overruled {overruled.length}× by deterministic code
              </div>
              <div className="text-xs text-haze">
                The model recommended promoting these to malicious; the trust layer withheld
                promotion for lack of corroborated proof. Click to inspect the gates →
              </div>
            </div>
          </div>
        </Link>
      )}

      {/* disposition scoreboard */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-haze">Disposition</h2>
        <Scoreboard caseId={caseId} counts={counts} />
      </section>

      {/* confirmed findings */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-haze">Confirmed malicious</h2>
          <Link href={`/case/${caseId}/findings`} className="text-sm text-brand link-ghost hover:!text-brand-glow">
            All findings →
          </Link>
        </div>
        {confirmed.length === 0 && <div className="panel p-5 text-sm text-haze">No findings cleared every gate.</div>}
        <div className="space-y-2.5">
          {confirmed.map((f) => (
            <Link key={f.finding_id} href={`/case/${caseId}/finding/${f.finding_id}`}
              className="panel flex items-center justify-between p-4 transition hover:border-brand/40">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-haze mono">{f.finding_id}</span>
                  <Severity level={f.severity} />
                </div>
                <div className="mt-0.5 truncate text-sm text-white">{f.title}</div>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="chip">{f.proof_count} proofs</span>
                <Pill bucket={f.disposition_bucket} />
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
