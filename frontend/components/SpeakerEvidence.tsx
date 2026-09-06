import type { SpeakerEvidence as Evidence, SpeakerSignal } from "@/lib/types";

const LABELS: Record<SpeakerSignal["name"], { title: string; rule: string }> = {
  talk_time: { title: "Talk time", rule: "teacher holds the floor longest" },
  pitch: { title: "Voice pitch", rule: "adult voice sits lower than children's" },
  voice_consistency: {
    title: "Voice consistency",
    rule: "one teacher voice is tighter than many student voices",
  },
};

function fmt(v: number | null, unit: string): string {
  if (v == null) return "—";
  if (unit === "s") return `${Math.round(v / 60)}m ${Math.round(v % 60)}s`;
  if (unit === "Hz") return `${Math.round(v)} Hz`;
  return v.toFixed(2);
}

/** Why the system decided which voice cluster is the teacher. */
export function SpeakerEvidencePanel({ evidence }: { evidence: Evidence }) {
  const overlay = evidence.degenerate_overlay;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
          How the teacher was identified
        </span>
        <span className="text-xs text-slate-500">
          {evidence.votes_for_teacher} of {evidence.votes_cast} signals agree
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {evidence.signals.map((s) => (
          <div
            key={s.name}
            className={`rounded-lg border p-3 ${
              s.agrees === false
                ? "border-amber-200 bg-amber-50/60"
                : "border-slate-100 bg-slate-50"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium">{LABELS[s.name].title}</span>
              <span
                className={`text-xs font-semibold ${
                  s.agrees === true
                    ? "text-emerald-600"
                    : s.agrees === false
                      ? "text-amber-600"
                      : "text-slate-400"
                }`}
              >
                {s.agrees === true ? "agrees" : s.agrees === false ? "disagrees" : "n/a"}
              </span>
            </div>
            <div className="mt-1.5 flex justify-between text-xs tabular-nums">
              <span className="text-indigo-600">T {fmt(s.teacher, s.unit)}</span>
              <span className="text-emerald-600">S {fmt(s.student, s.unit)}</span>
            </div>
            <p className="mt-1 text-[11px] leading-snug text-slate-400">
              {LABELS[s.name].rule}
            </p>
          </div>
        ))}
      </div>
      {evidence.note && (
        <p className="mt-3 text-xs text-slate-500">{evidence.note}.</p>
      )}
      {overlay && (
        <p className="mt-1 text-xs text-slate-500">
          Clustering collapsed on this recording (minority voice held{" "}
          {(overlay.minority_share * 100).toFixed(1)}% of talk time), so{" "}
          {overlay.segments_relabelled_student} segments were reassigned to students:{" "}
          {overlay.by_short_duration_only} for being short,{" "}
          {overlay.by_high_pitch_only} for being pitched well above the teacher
          {overlay.teacher_median_f0_hz != null && (
            <> ({Math.round(overlay.teacher_median_f0_hz)} Hz)</>
          )}
          , {overlay.by_both} for both.
        </p>
      )}
    </div>
  );
}
