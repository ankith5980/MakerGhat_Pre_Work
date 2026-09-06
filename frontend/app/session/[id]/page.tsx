"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { MetricCard } from "@/components/MetricCard";
import { SessionTimeline } from "@/components/SessionTimeline";
import { SpeakerEvidencePanel } from "@/components/SpeakerEvidence";
import { StatTile } from "@/components/StatTile";
import { TranscriptView } from "@/components/TranscriptView";
import {
  formatDuration,
  languageName,
  type SessionDetail,
} from "@/lib/types";

export default function SessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch(`/api/sessions/${id}`);
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        const data: SessionDetail = await res.json();
        if (cancelled) return;
        setSession(data);
        if (data.status === "processing") setTimeout(load, 4000);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : String(e));
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error)
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Could not load session: {error}
      </div>
    );
  if (!session) return <p className="text-sm text-slate-500">Loading…</p>;
  if (session.status === "processing")
    return (
      <p className="text-sm text-slate-500">
        Still processing this recording… the page will refresh automatically.
      </p>
    );

  const { stats, metrics, transcript, summary, meta } = session;

  return (
    <div className="space-y-8">
      <div>
        <Link href="/" className="text-sm text-indigo-600 hover:underline">
          ← All sessions
        </Link>
        <div className="mt-2 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-2xl font-semibold">
            {meta?.activityType ?? session.filename}
          </h2>
          <p className="text-sm text-slate-500">
            {meta?.teacherName && <>Teacher: {meta.teacherName} · </>}
            {meta?.totalStudents != null && (
              <>
                {meta.totalStudents} students ({meta.boys ?? "?"} boys,{" "}
                {meta.girls ?? "?"} girls) ·{" "}
              </>
            )}
            {meta?.timestamp}
          </p>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          {languageName(session.language)} · {formatDuration(session.duration_s)}{" "}
          · speaker separation: {session.diarization_method} · transcribed
          locally with Whisper ({session.processing_time_s}s)
        </p>
      </div>

      {stats && (
        <section>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Classroom overview
          </h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile
              label="Talk time split"
              value={`${Math.round(stats.teacher_talk_pct)}% / ${Math.round(stats.student_talk_pct)}%`}
              hint="teacher / student share of speech"
            >
              <div className="mt-2 flex h-2.5 w-full overflow-hidden rounded-full">
                <div
                  className="bg-indigo-500"
                  style={{ width: `${stats.teacher_talk_pct}%` }}
                  title={`Teacher ${stats.teacher_talk_pct}%`}
                />
                <div
                  className="flex-1 bg-emerald-400"
                  title={`Students ${stats.student_talk_pct}%`}
                />
              </div>
              <div className="mt-1 flex justify-between text-[11px] text-slate-400">
                <span>■ Teacher {formatDuration(stats.teacher_talk_s)}</span>
                <span className="text-emerald-600">
                  ■ Students {formatDuration(stats.student_talk_s)}
                </span>
              </div>
            </StatTile>
            <StatTile
              label="Teacher questions"
              value={String(stats.teacher_questions)}
              hint={`${stats.student_responses} drew a student response`}
            />
            <StatTile
              label="Student turns"
              value={String(stats.student_turns)}
              hint={`${stats.speaker_switches} teacher↔student switches`}
            />
            <StatTile
              label="Silence"
              value={formatDuration(stats.silence_total_s)}
              hint={`longest pause ${formatDuration(stats.longest_silence_s)}`}
            />
          </div>
        </section>
      )}

      {transcript && session.duration_s != null && (
        <SessionTimeline lines={transcript} duration={session.duration_s} />
      )}

      {session.speaker_evidence && (
        <SpeakerEvidencePanel evidence={session.speaker_evidence} />
      )}

      {metrics && (
        <section>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Engagement metrics
          </h3>
          <div className="grid gap-4 sm:grid-cols-2">
            {metrics.map((m) => (
              <MetricCard key={m.key} metric={m} />
            ))}
          </div>
        </section>
      )}

      {summary && (
        <section>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Classroom summary
          </h3>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-5 text-sm leading-relaxed text-slate-700">
            {summary}
          </div>
        </section>
      )}

      {transcript && (
        <section>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Transcript ({transcript.length} segments)
          </h3>
          <TranscriptView lines={transcript} />
        </section>
      )}
    </div>
  );
}
