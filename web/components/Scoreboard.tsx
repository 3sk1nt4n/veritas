import Link from "next/link";
import { BUCKETS } from "@/lib/queries";
import { BUCKET_META } from "./ui";

export function Scoreboard({
  caseId,
  counts,
}: {
  caseId: string;
  counts: Record<string, number>;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      {BUCKETS.map((b) => {
        const m = BUCKET_META[b];
        const n = counts[b] ?? 0;
        return (
          <Link
            key={b}
            href={`/case/${caseId}/findings?bucket=${b}`}
            className={`panel block px-4 py-3 transition hover:border-brand/40 ${n === 0 ? "opacity-50" : ""}`}
          >
            <div className={`stat-num ${m.text}`}>{n}</div>
            <div className="mt-1 flex items-center gap-1.5 text-xs text-haze">
              <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
              {m.label}
            </div>
          </Link>
        );
      })}
    </div>
  );
}
