"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { UploadCard } from "@/components/UploadCard";
import {
  formatDuration,
  languageName,
  type SessionSummary,
} from "@/lib/types";

export default function Dashboard() {
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      setSessions(data.sessions);
      setError(null);
    } catch {
      setError(
        "Could not reach the analysis backend. Start it with: uvicorn app.main:app --port 8000 (from the backend folder)."
      );
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while any session is still processing
  useEffect(() => {
    const anyProcessing = sessions?.some((s) => s.status === "processing");
    if (anyProcessing && !pollRef.current) {
      pollRef.current = setInterval(refresh, 4000);
    }
    if (!anyProcessing && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [sessions, refresh]);

  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-linear-to-r from-indigo-600 to-violet-600 p-6 text-white shadow-sm">
        <h2 className="text-xl font-semibold">
          What actually happens inside the classroom?
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-indigo-100">
          Upload a classroom recording (Hindi or English). The system
          transcribes it locally with Whisper, separates teacher and student
          speech using speaker-embedding clustering, and computes engagement
          metrics — no cloud APIs required.
        </p>
      </section>

      <UploadCard onUploaded={refresh} />

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Analyzed sessions
        </h3>
        {error && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800">
            {error}
          </div>
        )}
        {!error && sessions === null && (
          <p className="text-sm text-slate-500">Loading…</p>
        )}
        {!error && sessions?.length === 0 && (
          <p className="text-sm text-slate-500">
            No sessions yet — upload a recording above, or run{" "}
            <code className="rounded bg-slate-100 px-1">
              python scripts/preprocess.py
            </code>{" "}
            in the backend to seed the provided classroom audio.
          </p>
        )}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sessions?.map((s) => (
            <SessionCard key={s.id} session={s} />
          ))}
        </div>
      </section>
    </div>
  );
}

function SessionCard({ session: s }: { session: SessionSummary }) {
  const dominance = s.stats
    ? Math.round(s.stats.teacher_talk_pct)
    : null;
  const card = (
    <div className="flex h-full flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-300 hover:shadow">
      <div>
        <div className="flex items-start justify-between gap-2">
          <h4 className="font-medium leading-snug">
            {s.meta?.activityType ?? s.filename ?? s.id}
          </h4>
          <StatusBadge status={s.status} />
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {s.meta?.teacherName && <>Teacher: {s.meta.teacherName} · </>}
          {s.meta?.totalStudents != null && <>{s.meta.totalStudents} students · </>}
          {s.meta?.timestamp ?? s.id}
        </p>
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <Chip>{languageName(s.language)}</Chip>
        <Chip>{formatDuration(s.duration_s)}</Chip>
        {dominance != null && <Chip>Teacher talk {dominance}%</Chip>}
        {s.stats && (
          <Chip>
            {s.stats.teacher_questions} question
            {s.stats.teacher_questions === 1 ? "" : "s"}
          </Chip>
        )}
      </div>
      {s.stats && (
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-emerald-200">
          <div
            className="h-full bg-indigo-500"
            style={{ width: `${s.stats.teacher_talk_pct}%` }}
          />
        </div>
      )}
      {s.status === "error" && (
        <p className="mt-2 text-xs text-red-600">{s.error}</p>
      )}
    </div>
  );

  if (s.status !== "done") return card;
  return <Link href={`/session/${s.id}`}>{card}</Link>;
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-slate-600">
      {children}
    </span>
  );
}

function StatusBadge({ status }: { status: SessionSummary["status"] }) {
  if (status === "processing")
    return (
      <span className="flex items-center gap-1.5 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
        processing
      </span>
    );
  if (status === "error")
    return (
      <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
        error
      </span>
    );
  return (
    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
      done
    </span>
  );
}
