import Link from "next/link";

export function Nav() {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-ink-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 place-items-center rounded-md border border-brand/40 bg-brand/10 text-brand">✓</span>
          <span className="text-sm font-semibold tracking-tight text-white">Veritas</span>
          <span className="hidden text-xs text-haze sm:inline">· the AI never gets the final word</span>
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/" className="link-ghost">Cases</Link>
          <Link href="/pivot" className="link-ghost">Cross-case pivot</Link>
          <a href="https://github.com/3sk1nt4n/Sentinel-Ensemble" target="_blank" rel="noreferrer" className="link-ghost">Engine ↗</a>
        </nav>
      </div>
    </header>
  );
}
