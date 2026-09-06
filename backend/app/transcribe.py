"""Audio -> text transcription using faster-whisper (offline after first model download)."""
from dataclasses import dataclass

from faster_whisper import WhisperModel

_model: WhisperModel | None = None

MODEL_SIZE = "small"  # multilingual: handles Hindi / Hinglish / English


@dataclass
class Segment:
    start: float
    end: float
    text: str


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> tuple[list[Segment], str, float]:
    """Returns (segments, language_code, audio_duration_seconds)."""
    model = get_model()
    raw_segments, info = model.transcribe(
        audio_path,
        # These recordings are hour-long phone captures of noisy classrooms;
        # most of the audio is ambient chatter. An aggressive VAD keeps Whisper
        # away from non-speech, and greedy, unconditioned, no-repeat decoding
        # prevents the hallucinated token loops that otherwise slow decoding
        # ~10x and fill the transcript with repeated words.
        vad_filter=True,
        vad_parameters={
            "threshold": 0.6,
            "min_silence_duration_ms": 700,
            "min_speech_duration_ms": 400,
        },
        beam_size=1,
        condition_on_previous_text=False,
        temperature=0.0,
        no_repeat_ngram_size=3,
        no_speech_threshold=0.5,
        compression_ratio_threshold=2.2,
    )
    segments = [
        Segment(start=s.start, end=s.end, text=s.text.strip())
        for s in raw_segments
        if s.text.strip()
    ]
    return segments, info.language, info.duration
