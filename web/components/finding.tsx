import { BUCKET_META, Tool, Mono, ENTITY_GLYPH } from "./ui";
import type { TraceRow, ClaimRow } from "@/lib/queries";

function dispoLabel(d: string | null) {
  if (!d) return "-";
  return BUCKET_META[d]?.label ?? d.replace(/_/g, " ");
}

/** The product's hero moment: the model wanted to promote this; deterministic
 *  code refused, and we show the exact gate. */
export function OverrulePanel({
  modelWanted,
  codeVerdict,
  reasons,
}: {
  modelWanted: string | null;
  codeVerdict: string;
  reasons: string[] | null;
}) {
  const gates = (reasons ?? []).filter(
    (r) => /gate|=fail|ineligible/i.test(r)
  );
  return (
    <section className="panel overflow-hidden border-brand/30 bg-brand/[0.05]">
      <div className="border-b border-line px-5 py-3 text-xs font-semibold uppercase tracking-wide text-brand-glow">
        ⚖ The AI did not get the final word
      </div>
      <div className="grid gap-3 p-5 md:grid-cols-[1fr_auto_1fr] md:items-center">
        <div className="rounded-lg border border-line bg-ink-900/60 p-4">
          <div className="text-[11px] uppercase tracking-wide text-haze">Model / ReAct proposed</div>
          <div className="mt-1 text-lg font-semibold text-confirmed">
            {dispoLabel(modelWanted === "confirmed_malicious" ? "confirmed_malicious_atomic" : modelWanted)}
          </div>
        </div>
        <div className="grid place-items-center text-2xl text-brand">→</div>
        <div className="rounded-lg border border-brand/40 bg-brand/10 p-4">
          <div className="text-[11px] uppercase tracking-wide text-haze">Veritas (deterministic) verdict</div>
          <div className={`mt-1 text-lg font-semibold ${BUCKET_META[codeVerdict]?.text}`}>
            {dispoLabel(codeVerdict)}
          </div>
        </div>
      </div>
      {gates.length > 0 && (
        <div className="border-t border-line px-5 py-4">
          <div className="mb-2 text-[11px] uppercase tracking-wide text-haze">Promotion withheld because</div>
          <ul className="space-y-1.5">
            {gates.map((g, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 text-suspicious">✕</span>
                <Mono className="!text-suspicious/90">{g}</Mono>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function Claims({ claims }: { claims: ClaimRow[] }) {
  if (!claims.length) return null;
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-haze">Claims asserted</h2>
      <div className="panel divide-y divide-line">
        {claims.map((c, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2 p-3 text-sm">
            <span className="chip">{c.claim_type ?? "claim"}</span>
            <span className="text-white">{c.claim_value ?? c.filename ?? "-"}</span>
            {c.sha1 && <Mono className="!text-haze">{c.sha1}</Mono>}
            <span className="ml-auto flex flex-wrap gap-1.5">
              {(c.source_tools ?? []).map((t) => <Tool key={t} name={t} />)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

/** claim -> fact -> tool: every proof, by foreign key. */
export function TraceTree({ trace }: { trace: TraceRow[] }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-haze">
        Proof chain · {trace.length} fact{trace.length === 1 ? "" : "s"}
      </h2>
      <p className="text-xs text-haze">
        Every confirmed claim links by foreign key to the typed fact that validated it, and to
        the forensic tool that produced that fact. This is one <code className="mono">finding_trace()</code> query.
      </p>
      <div className="space-y-2">
        {trace.map((t, i) => {
          const kind = (t.canonical_entity_id ?? "").split(":")[0];
          return (
            <details key={i} className="panel group overflow-hidden [&_summary::-webkit-details-marker]:hidden">
              <summary className="flex cursor-pointer items-center gap-3 p-3.5">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-line bg-ink-900 text-brand">
                  {ENTITY_GLYPH[kind] ?? "•"}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-white">{(t.fact_type ?? "fact").replace(/_/g, " ")}</span>
                    {t.canonical_entity_id && <Mono className="!text-haze">{t.canonical_entity_id}</Mono>}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    {(t.source_tools ?? []).map((tool) => <Tool key={tool} name={tool} />)}
                    {!t.source_tools?.length && <span className="text-xs text-haze">referenced (outside ingested subset)</span>}
                  </div>
                </div>
                <span className="text-haze transition group-open:rotate-90">›</span>
              </summary>
              {t.raw_excerpt && (
                <div className="border-t border-line bg-ink-950/60 p-3">
                  <div className="mb-1 text-[10px] uppercase tracking-wide text-haze">Raw tool output · {t.fact_signature}</div>
                  <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words text-[12px] leading-relaxed text-slate-300 mono">
                    {t.raw_excerpt}
                  </pre>
                </div>
              )}
            </details>
          );
        })}
      </div>
    </section>
  );
}
