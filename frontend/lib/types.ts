export interface SessionMeta {
  activityType?: string;
  teacherName?: string;
  teacherId?: string;
  totalStudents?: number;
  boys?: number;
  girls?: number;
  timestamp?: string;
}

export interface SessionStats {
  duration_s: number;
  teacher_talk_s: number;
  student_talk_s: number;
  teacher_talk_pct: number;
  student_talk_pct: number;
  teacher_turns: number;
  student_turns: number;
  teacher_questions: number;
  student_responses: number;
  speaker_switches: number;
  silence_total_s: number;
  longest_silence_s: number;
}

export interface Metric {
  key: string;
  name: string;
  value: number;
  display: string;
  formula: string;
  explanation: string;
  interpretation: string;
}

export interface TranscriptLine {
  start: number;
  end: number;
  speaker: "teacher" | "student";
  text: string;
  is_question: boolean;
}

export interface SessionSummary {
  id: string;
  filename: string;
  status: "processing" | "done" | "error";
  language?: string;
  duration_s?: number;
  meta?: SessionMeta;
  stats?: SessionStats;
  error?: string;
}

export interface SessionDetail extends SessionSummary {
  diarization_method?: string;
  processing_time_s?: number;
  transcript?: TranscriptLine[];
  metrics?: Metric[];
  summary?: string;
}

export const LANGUAGE_NAMES: Record<string, string> = {
  hi: "Hindi",
  en: "English",
  mr: "Marathi",
  bn: "Bengali",
  ta: "Tamil",
  te: "Telugu",
  kn: "Kannada",
  ml: "Malayalam",
  gu: "Gujarati",
  pa: "Punjabi",
  or: "Odia",
  ur: "Urdu",
};

export function languageName(code?: string): string {
  if (!code) return "—";
  return LANGUAGE_NAMES[code] ?? code.toUpperCase();
}

export function formatDuration(seconds?: number): string {
  if (seconds == null) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`;
}

export function formatClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
