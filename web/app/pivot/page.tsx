import Link from "next/link";
import { pivotSearch, casesByIds } from "@/lib/queries";
import { Crumbs, Mono, ENTITY_GLYPH } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function PivotPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q = "" } = await searchParams;
  const rows = await pivotSearch(q);

  const allCaseIds = Array.from(new Set(rows.flatMap((r) => r.case_ids ?? [])));
  const caseMap = new Map((await casesByIds(allCaseIds)).map((c) => [c.case_id, c.case_name]));

  return (
    <div className="space-y-6">
      <Crumbs items={[{ href: "/", label: "Cases" }, { label: "Cross-case pivot" }]} />

      <section>
        <h1 className="text-xl font-semibold tracking-tight text-white">Cross-case IOC pivot</h1>
        <p className="mt-1 max-w-2xl text-sm text-haze">
          Type any entity - a hash, IP, PID, registry key - and see every case it appears in.
          This is one indexed Aurora query across the entire corpus; the file-based engine
          cannot do it.
        </p>
        <form className="mt-4 flex gap-2" action="/pivot" method="get">
          <input
            name="q"
            defaultValue={q}
            placeholder="e.g. 8712, psexec, perfmon…"
            className="w-full rounded-lg border border-line bg-ink-900 px-4 py-2.5 text-sm text-white outline-none placeholder:text-haze/60 focus:border-brand/50"
          />
          <button className="rounded-lg border border-brand/40 bg-brand/10 px-4 py-2.5 text-sm font-medium text-brand-glow transition hover:bg-brand/20">
            Pivot
          </button>
        </form>
        <p className="mt-2 text-xs text-haze">
          {q ? `Matches for “${q}”` : "Showing entities that appear in more than one case."}
        </p>
      </section>

      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-line text-left text-xs uppercase tracking-wide text-haze">
            <tr>
              <th className="px-4 py-2.5 font-medium">Entity</th>
              <th className="px-4 py-2.5 font-medium">Kind</th>
              <th className="px-4 py-2.5 text-right font-medium">Cases</th>
              <th className="px-4 py-2.5 text-right font-medium">Facts</th>
              <th className="px-4 py-2.5 font-medium">Seen in</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((r, i) => (
              <tr key={i} className="hover:bg-ink-800/40">
                <td className="px-4 py-2.5">
                  <span className="mr-2 text-brand">{ENTITY_GLYPH[r.entity_kind] ?? "•"}</span>
                  <Mono className="!text-slate-200">{r.entity_value}</Mono>
                </td>
                <td className="px-4 py-2.5 text-haze">{r.entity_kind}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  <span className={r.case_count > 1 ? "font-semibold text-brand" : "text-haze"}>{r.case_count}</span>
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-haze">{r.fact_count}</td>
                <td className="px-4 py-2.5">
                  <div className="flex flex-wrap gap-1.5">
                    {(r.case_ids ?? []).map((id) => (
                      <Link key={id} href={`/case/${id}`} className="chip hover:border-brand/40 hover:text-white">
                        {caseMap.get(id) ?? id.slice(0, 8)}
                      </Link>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-haze">No matching entities.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
