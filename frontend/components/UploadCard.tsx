"use client";

import { useRef, useState } from "react";

export function UploadCard({ onUploaded }: { onUploaded: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function upload(file: File) {
    setBusy(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/analyze", { method: "POST", body: form });
      if (!res.ok) throw new Error(`upload failed (${res.status})`);
      setMessage(
        `“${file.name}” uploaded — transcription is running locally. This can take a few minutes for long recordings; the card below will update automatically.`
      );
      onUploaded();
    } catch (e) {
      setMessage(
        `Upload failed: ${e instanceof Error ? e.message : String(e)}. Is the backend running on port 8000?`
      );
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <section
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file) upload(file);
      }}
      className={`rounded-2xl border-2 border-dashed p-6 text-center transition ${
        dragOver
          ? "border-indigo-400 bg-indigo-50"
          : "border-slate-300 bg-white"
      }`}
    >
      <p className="font-medium">Analyze a new classroom recording</p>
      <p className="mt-1 text-sm text-slate-500">
        Drag &amp; drop an audio file here (mp3 / wav / m4a), or
      </p>
      <button
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        className="mt-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
      >
        {busy ? "Uploading…" : "Choose audio file"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="audio/*,.mp3,.wav,.m4a,.ogg,.flac"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload(file);
        }}
      />
      {message && (
        <p className="mx-auto mt-3 max-w-xl text-xs text-slate-600">{message}</p>
      )}
    </section>
  );
}
