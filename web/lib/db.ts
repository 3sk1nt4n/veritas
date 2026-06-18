import { Pool } from "pg";

// One pooled connection per server runtime. Works against local Postgres and,
// in production, against Amazon Aurora over SSL via a direct pooled connection
// (set PGSSL=require for Aurora). RDS Proxy / the Data API are a drop-in upgrade
// behind the same connection string.
const globalForPg = globalThis as unknown as { __veritasPool?: Pool };

const CONN =
  process.env.DATABASE_URL ?? "postgresql://postgres:veritas@localhost:5433/veritas";
// Aurora requires SSL; the local Docker Postgres does not. Decide by host so a
// missing or mistyped PGSSL can never break the cloud connection.
const IS_LOCAL = /@(localhost|127\.0\.0\.1|host\.docker\.internal)/.test(CONN);

export const pool: Pool =
  globalForPg.__veritasPool ??
  new Pool({
    connectionString: CONN,
    max: 5,
    ssl: IS_LOCAL && process.env.PGSSL !== "require" ? undefined : { rejectUnauthorized: false },
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
