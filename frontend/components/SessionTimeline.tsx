import type { TranscriptLine } from "@/lib/types";

/** Horizontal strip showing who is speaking across the session; gaps are silence. */
export function SessionTimeline({
  lines,
  duration,
}: {
  lines: TranscriptLine[];
  duration: number;
}) {
  if (!duration || lines.length === 0) return null;
  const pct = (s: number) => `${Math.min(100, Math.max(0, (s / duration) * 100))}%`;
  const minutes = Math.round(duration / 60);
  const tickEvery = minutes > 45 ? 10 : 5;
  const ticks = [];
  for (let m = tickEvery; m < minutes; m += tickEvery) ticks.push(m);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
        <span className="font-medium uppercase tracking-wide text-slate-400">
          Session timeline
        </span>
        <span>
          <span className="mr-3 text-indigo-600">■ teacher</span>
          <span className="mr-3 text-emerald-600">■ student</span>
          <span className="text-slate-400">░ silence / noise</span>
        </span>
      </div>
      <div className="relative h-6 w-full overflow-hidden rounded-md bg-slate-100">
        {lines.map((l, i) => (
          <div
            key={`${l.start}-${i}`}
            className={`absolute top-0 h-full ${
              l.speaker === "teacher" ? "bg-indigo-500" : "bg-emerald-500"
            }`}
            style={{
              left: pct(l.start),
              width: `max(2px, calc(${pct(l.end)} - ${pct(l.start)}))`,
            }}
            title={`${l.speaker} · ${Math.floor(l.start / 60)}:${String(Math.floor(l.start % 60)).padStart(2, "0")}`}
          />
        ))}
      </div>
      <div className="relative mt-1 h-4 text-[10px] text-slate-400">
        <span className="absolute left-0">0:00</span>
        {ticks.map((m) => (
          <span
            key={m}
            className="absolute -translate-x-1/2"
            style={{ left: pct(m * 60) }}
          >
            {m}m
          </span>
        ))}
        <span className="absolute right-0">{minutes}m</span>
      </div>
    </div>
  );
}
