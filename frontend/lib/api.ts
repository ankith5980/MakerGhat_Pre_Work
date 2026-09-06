import type { SessionDetail, SessionSummary } from "./types";

/**
 * Where session data comes from.
 *  - "api":    the FastAPI backend, reached through the /api rewrite in next.config.
 *  - "static": the pre-computed JSON committed under public/results/ — lets a hosted
 *              demo serve every session with no backend at all.
 * Production builds default to static so a Vercel deploy needs no configuration;
 * set NEXT_PUBLIC_BACKEND_URL (or NEXT_PUBLIC_DATA_MODE=api) to use a hosted backend.
 */
export const DATA_MODE: "api" | "static" =
  (process.env.NEXT_PUBLIC_DATA_MODE as "api" | "static" | undefined) ??
  (process.env.NEXT_PUBLIC_BACKEND_URL
    ? "api"
    : process.env.NODE_ENV === "production"
      ? "static"
      : "api");

export const IS_STATIC = DATA_MODE === "static";

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} returned ${res.status}`);
  return res.json() as Promise<T>;
}

export async function fetchSessions(): Promise<SessionSummary[]> {
  const data = await getJson<{ sessions: SessionSummary[] }>(
    IS_STATIC ? "/results/index.json" : "/api/sessions"
  );
  return data.sessions;
}

export async function fetchSession(id: string): Promise<SessionDetail> {
  const safe = encodeURIComponent(id);
  return getJson<SessionDetail>(
    IS_STATIC ? `/results/${safe}.json` : `/api/sessions/${safe}`
  );
}
