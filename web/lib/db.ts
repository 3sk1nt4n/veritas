import { Pool } from "pg";

// One pooled connection per server runtime. Works against local Postgres and,
// in production, against Amazon Aurora through RDS Proxy / the Data API endpoint
// (same connection string; set PGSSL=require for Aurora).
const globalForPg = globalThis as unknown as { __veritasPool?: Pool };

export const pool: Pool =
  globalForPg.__veritasPool ??
  new Pool({
    connectionString:
      process.env.DATABASE_URL ??
      "postgresql://postgres:veritas@localhost:5433/veritas",
    max: 5,
    ssl: process.env.PGSSL === "require" ? { rejectUnauthorized: false } : undefined,
  });

if (!globalForPg.__veritasPool) globalForPg.__veritasPool = pool;

export async function q<T = Record<string, unknown>>(
  text: string,
  params: unknown[] = []
): Promise<T[]> {
  const res = await pool.query(text, params);
  return res.rows as T[];
}

export async function q1<T = Record<string, unknown>>(
  text: string,
  params: unknown[] = []
): Promise<T | null> {
  const rows = await q<T>(text, params);
  return rows[0] ?? null;
}
