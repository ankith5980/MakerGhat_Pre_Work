// Copies the backend's analysis results into public/results/ so a static build can
// serve them without a backend. Run after re-processing audio: `npm run sync-results`.
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "..", "backend", "data", "results");
const dst = join(here, "..", "public", "results");

mkdirSync(dst, { recursive: true });

const sessions = [];
for (const file of readdirSync(src).filter((f) => f.endsWith(".json")).sort()) {
  const d = JSON.parse(readFileSync(join(src, file), "utf8"));
  if (d.status !== "done") continue;
  writeFileSync(join(dst, file), JSON.stringify(d));
  // Same shape the backend's GET /api/sessions returns.
  sessions.push({
    id: d.id,
    filename: d.filename,
    status: d.status,
    language: d.language,
    duration_s: d.duration_s,
    meta: d.meta ?? {},
    stats: d.stats ?? null,
    error: d.error ?? null,
  });
}
writeFileSync(join(dst, "index.json"), JSON.stringify({ sessions }));
console.log(`synced ${sessions.length} sessions to public/results/`);
