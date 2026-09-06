"""Batch-process the provided classroom audio folders into result JSONs.

Usage (from backend/):  python scripts/preprocess.py [--limit N]
Each session folder in data/audio/ contains <id>.mp3 and <id>.json (metadata).
"""
import argparse
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline import RESULTS_DIR, process_audio  # noqa: E402

AUDIO_DIR = Path(__file__).resolve().parent.parent / "data" / "audio"

META_KEYS = ["activityType", "teacherId", "totalStudents", "boys", "girls", "timestamp"]


def load_meta(folder: Path, session_id: str) -> dict:
    meta_path = folder / f"{session_id}.json"
    if not meta_path.exists():
        return {}
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    meta = {k: raw[k] for k in META_KEYS if k in raw}
    teacher_name = (raw.get("photoMetadata") or {}).get("teacherName")
    if teacher_name:
        meta["teacherName"] = teacher_name
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="process at most N sessions")
    parser.add_argument("--force", action="store_true", help="re-process existing results")
    args = parser.parse_args()

    folders = sorted(p for p in AUDIO_DIR.iterdir() if p.is_dir())
    if args.limit:
        folders = folders[: args.limit]

    for folder in folders:
        session_id = folder.name
        out = RESULTS_DIR / f"{session_id}.json"
        if out.exists() and not args.force:
            existing = json.loads(out.read_text(encoding="utf-8"))
            if existing.get("status") == "done":
                print(f"[skip] {session_id} already processed")
                continue
        mp3s = list(folder.glob("*.mp3")) + list(folder.glob("*.wav")) + list(folder.glob("*.m4a"))
        if not mp3s:
            print(f"[skip] {session_id}: no audio file found")
            continue
        print(f"[proc] {session_id} ...", flush=True)
        try:
            result = process_audio(str(mp3s[0]), session_id, meta=load_meta(folder, session_id))
            stats = result["stats"]
            print(
                f"[done] {session_id}: lang={result['language']} "
                f"dur={result['duration_s']}s teacher={stats['teacher_talk_pct']}% "
                f"questions={stats['teacher_questions']} "
                f"({result['processing_time_s']}s to process)",
                flush=True,
            )
        except Exception:
            traceback.print_exc()
            print(f"[fail] {session_id}", flush=True)


if __name__ == "__main__":
    main()
