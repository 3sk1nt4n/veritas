import Link from "next/link";
import { notFound } from "next/navigation";
import { getCase, listFindings, getScoreboard, BUCKETS, BUCKET_LABEL } from "@/lib/queries";
import { Crumbs, Severity, Pill, Tool } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function FindingsPage({
  params,
  searchParams,
}: {
  params: Promise<{ caseId: string }>;
  searchParams: Promise<{ bucket?: string }>;
}) {
  const { caseId } = await params;
  const { bucket } = await searchParams;
  const c = await getCase(caseId);
  if (!c) notFound();

  const [findings, counts] = await Promise.all([
    listFindings(caseId, bucket),
    getScoreboard(caseId),
  ]);

  return (
    <div className="space-y-6">
      <Crumbs items={[{ href: "/", label: "Cases" }, { href: `/case/${caseId}`, label: c.case_name }, { label: "Findings" }]} />

      <div className="flex flex-wrap items-center gap-2">
        <FilterPill caseId={caseId} active={!bucket} label="All" count={c.finding_count} />
        {BUCKETS.map((b) =>
          counts[b] > 0 ? (
            <FilterPill key={b} caseId={caseId} bucket={b} active={bucket === b} label={BUCKET_LABEL[b]} count={counts[b]} />
          ) : null
        )}
      </div>

      <div className="space-y-2.5">
        {findings.map((f) => (
          <Link key={f.finding_id} href={`/case/${caseId}/finding/${f.finding_id}`}
            className="panel block p-4 transition hover:border-brand/40">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-haze mono">{f.finding_id}</span>
                  <Severity level={f.severity} />
                  {f.ai_overruled && (
                    <span className="chip border-brand/30 bg-brand/10 text-brand-glow">⚖ AI overruled</span>
                  )}
                </div>
                <div className="mt-1 text-sm text-white">{f.title}</div>
                {f.source_tools?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {f.source_tools.slice(0, 4).map((t) => <Tool key={t} name={t} />)}
                    {f.source_tools.length > 4 && <span className="chip">+{f.source_tools.length - 4}</span>}
                  </div>
                )}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-2">
                <Pill bucket={f.disposition_bucket} />
                <span className="chip">{f.proof_count} proofs</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function FilterPill({
  caseId, bucket, active, label, count,
}: { caseId: string; bucket?: string; active: boolean; label: string; count: number }) {
  const href = bucket ? `/case/${caseId}/findings?bucket=${bucket}` : `/case/${caseId}/findings`;
  return (
    <Link href={href}
      className={`rounded-lg border px-3 py-1.5 text-sm transition ${
        active ? "border-brand/50 bg-brand/10 text-white" : "border-line bg-ink-850/60 text-haze hover:text-white"
      }`}>
      {label} <span className="ml-1 tabular-nums opacity-70">{count}</span>
    </Link>
  );
}
