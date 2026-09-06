"""Full processing pipeline: audio file -> analysis result JSON."""
import json
import time
from pathlib import Path

from .analyze import analyze
from .diarize import label_speakers
from .transcribe import transcribe

BACKEND_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BACKEND_DIR / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def process_audio(audio_path: str, session_id: str, meta: dict | None = None) -> dict:
    started = time.time()
    segments, language, duration = transcribe(audio_path)
    labels, method, evidence = label_speakers(audio_path, segments)
    analysis = analyze(segments, labels, duration)
    result = {
        "id": session_id,
        "filename": Path(audio_path).name,
        "status": "done",
        "language": language,
        "duration_s": round(duration, 1),
        "diarization_method": method,
        "speaker_evidence": evidence,
        "processing_time_s": round(time.time() - started, 1),
        "meta": meta or {},
        **analysis,
    }
    save_result(result)
    return result


def save_result(result: dict) -> None:
    path = RESULTS_DIR / f"{result['id']}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def load_results_index() -> list[dict]:
    items = []
    for path in sorted(RESULTS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        items.append({
            "id": data.get("id", path.stem),
            "filename": data.get("filename", ""),
            "status": data.get("status", "done"),
            "language": data.get("language"),
            "duration_s": data.get("duration_s"),
            "meta": data.get("meta", {}),
            "stats": data.get("stats"),
            "error": data.get("error"),
        })
    return items


def load_result(session_id: str) -> dict | None:
    path = RESULTS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
