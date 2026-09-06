"""FastAPI app for the Classroom Voice Analytics MVP."""
import re
import threading
import time
import traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .pipeline import BACKEND_DIR, load_result, load_results_index, process_audio, save_result

UPLOADS_DIR = BACKEND_DIR / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Classroom Voice Analytics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run_pipeline(audio_path: str, session_id: str, filename: str) -> None:
    try:
        process_audio(audio_path, session_id)
    except Exception as exc:
        traceback.print_exc()
        save_result({
            "id": session_id,
            "filename": filename,
            "status": "error",
            "error": str(exc),
        })


@app.post("/api/analyze")
async def analyze_upload(file: UploadFile):
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(file.filename or "upload").stem)[:60]
    session_id = f"{safe_stem}_{int(time.time())}"
    suffix = Path(file.filename or "").suffix or ".mp3"
    dest = UPLOADS_DIR / f"{session_id}{suffix}"
    dest.write_bytes(await file.read())

    save_result({
        "id": session_id,
        "filename": file.filename,
        "status": "processing",
    })
    threading.Thread(
        target=_run_pipeline, args=(str(dest), session_id, file.filename), daemon=True
    ).start()
    return {"session_id": session_id, "status": "processing"}


@app.get("/api/sessions")
def list_sessions():
    return {"sessions": load_results_index()}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    result = load_result(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="session not found")
    return result
