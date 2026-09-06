"use client";

import { useState } from "react";
import { formatClock, type TranscriptLine } from "@/lib/types";

type Filter = "all" | "teacher" | "student" | "questions";

export function TranscriptView({ lines }: { lines: TranscriptLine[] }) {
  const [filter, setFilter] = useState<Filter>("all");

  const visible = lines.filter((l) => {
    if (filter === "all") return true;
    if (filter === "questions") return l.is_question;
    return l.speaker === filter;
  });

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3">
        {(
          [
            ["all", "All"],
            ["teacher", "Teacher"],
            ["student", "Students"],
            ["questions", "Questions"],
          ] as [Filter, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              filter === key
                ? "bg-indigo-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {label}
          </button>
        ))}
        <span className="ml-auto text-xs text-slate-400">
          {visible.length} of {lines.length} segments
        </span>
      </div>
      <div className="max-h-[32rem] space-y-2 overflow-y-auto p-4">
        {visible.map((l, i) => (
          <div
            key={`${l.start}-${i}`}
            className={`flex ${l.speaker === "teacher" ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                l.speaker === "teacher"
                  ? "rounded-tl-sm bg-indigo-50 text-slate-800"
                  : "rounded-tr-sm bg-emerald-50 text-slate-800"
              }`}
            >
              <div className="mb-0.5 flex items-center gap-2 text-[11px] text-slate-400">
                <span
                  className={`font-semibold ${
                    l.speaker === "teacher"
                      ? "text-indigo-600"
                      : "text-emerald-600"
                  }`}
                >
                  {l.speaker === "teacher" ? "Teacher" : "Student"}
                </span>
                <span>{formatClock(l.start)}</span>
                {l.is_question && (
                  <span className="rounded-full bg-amber-100 px-1.5 py-0.5 font-medium text-amber-700">
                    question
                  </span>
                )}
              </div>
              {l.text}
            </div>
          </div>
        ))}
        {visible.length === 0 && (
          <p className="text-sm text-slate-400">Nothing matches this filter.</p>
        )}
      </div>
    </div>
  );
}
