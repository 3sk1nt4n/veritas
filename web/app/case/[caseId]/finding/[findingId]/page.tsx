import { notFound } from "next/navigation";
import { getCase, getFinding, getClaims, getTrace } from "@/lib/queries";
import { Crumbs, Severity, Pill, Tool } from "@/components/ui";
import { OverrulePanel, Claims, TraceTree } from "@/components/finding";

export const dynamic = "force-dynamic";

export default async function FindingPage({
  params,
}: {
  params: Promise<{ caseId: string; findingId: string }>;
}) {
  const { caseId, findingId } = await params;
  const [c, f] = await Promise.all([getCase(caseId), getFinding(caseId, findingId)]);
  if (!c || !f) notFound();

  const [claims, trace] = await Promise.all([
    getClaims(caseId, findingId),
    getTrace(caseId, findingId),
  ]);

  return (
    <div className="space-y-7">
      <Crumbs
        items={[
          { href: "/", label: "Cases" },
          { href: `/case/${caseId}`, label: c.case_name },
          { href: `/case/${caseId}/findings`, label: "Findings" },
          { label: f.finding_id },
        ]}
      />

      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-haze mono">{f.finding_id}</span>
          <Severity level={f.severity} />
          <Pill bucket={f.disposition_bucket} />
          {f.deterministic_check && (
            <span className="chip border-benign/30 bg-benign/10 text-benign">
              validator: {f.deterministic_check}
            </span>
          )}
        </div>
        <h1 className="text-2xl font-semibold leading-snug tracking-tight text-white">{f.title}</h1>
        {f.artifact && <p className="text-sm text-haze mono">{f.artifact}</p>}
      </header>

      {f.ai_overruled && (
        <OverrulePanel
          modelWanted={f.model_recommended_disposition}
          codeVerdict={f.disposition_bucket}
          reasons={f.disposition_reasons}
        />
      )}

      {f.description && (
        <section className="panel p-5">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-haze">Analyst narrative</div>
          <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-slate-200">{f.description}</p>
        </section>
      )}

      <Claims claims={claims} />
      <TraceTree trace={trace} />

      {f.source_tools?.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-haze">Source tools</h2>
          <div className="flex flex-wrap gap-1.5">
            {f.source_tools.map((t) => <Tool key={t} name={t} />)}
          </div>
        </section>
      )}
    </div>
  );
}
