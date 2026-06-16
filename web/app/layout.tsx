import "./globals.css";
import type { Metadata } from "next";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "Veritas — the AI never gets the final word",
  description:
    "A chain-of-custody platform for AI-assisted investigations. Deterministic code decides what is confirmed; every finding traces to the tool that proved it. Built on Amazon Aurora PostgreSQL.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen font-sans antialiased">
        <Nav />
        <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-5 py-10 text-xs text-haze">
          Veritas · Track 2 (B2B) · Amazon Aurora PostgreSQL Serverless v2 + Vercel ·
          data ingested from real{" "}
          <a className="link-ghost underline" href="https://github.com/3sk1nt4n/Sentinel-Ensemble" target="_blank" rel="noreferrer">
            Sentinel Ensemble
          </a>{" "}
          runs.
        </footer>
      </body>
    </html>
  );
}
