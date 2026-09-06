"""Re-run diarization + analysis on already-transcribed results (no re-transcription).

Usage (from backend/):  python scripts/relabel.py [session_id ...]
Without arguments, relabels every 'done' result that has a matching audio file.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analyze import analyze  # noqa: E402
from app.diarize import label_speakers  # noqa: E402
from app.pipeline import RESULTS_DIR, save_result  # noqa: E402
from app.transcribe import Segment  # noqa: E402

AUDIO_DIR = Path(__file__).resolve().parent.parent / "data" / "audio"
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"


def find_audio(session_id: str) -> Path | None:
    folder = AUDIO_DIR / session_id
    if folder.is_dir():
        for ext in ("*.mp3", "*.wav", "*.m4a"):
            hits = list(folder.glob(ext))
            if hits:
                return hits[0]
    hits = list(UPLOADS_DIR.glob(f"{session_id}.*"))
    return hits[0] if hits else None


def main() -> None:
    ids = sys.argv[1:] or [p.stem for p in sorted(RESULTS_DIR.glob("*.json"))]
    for session_id in ids:
        path = RESULTS_DIR / f"{session_id}.json"
        if not path.exists():
            print(f"[skip] {session_id}: no result file")
            continue
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("status") != "done" or not result.get("transcript"):
            print(f"[skip] {session_id}: status={result.get('status')}")
            continue
        audio = find_audio(session_id)
        if audio is None:
            print(f"[skip] {session_id}: audio file not found")
            continue
        segments = [
            Segment(start=t["start"], end=t["end"], text=t["text"])
            for t in result["transcript"]
        ]
        labels, method, evidence = label_speakers(str(audio), segments)
        result.update(analyze(segments, labels, result["duration_s"]))
        result["diarization_method"] = method
        result["speaker_evidence"] = evidence
        save_result(result)
        stats = result["stats"]
        pitch = next((s for s in (evidence or {}).get("signals", []) if s["name"] == "pitch"), None)
        pitch_txt = (
            f" pitch T={pitch['teacher']}Hz S={pitch['student']}Hz" if pitch and pitch["teacher"] else ""
        )
        votes_txt = (
            f" votes={evidence['votes_for_teacher']}/{evidence['votes_cast']}" if evidence else ""
        )
        print(
            f"[done] {session_id}: method={method}{votes_txt}{pitch_txt} "
            f"teacher={stats['teacher_talk_pct']}% student_turns={stats['student_turns']} "
            f"switches={stats['speaker_switches']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
