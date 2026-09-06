"""Approximate teacher/student separation.

Strategy: split every transcript segment into short windows, embed each window
with SpeechBrain ECAPA-TDNN, cluster the windows into 2 groups, and label each
segment by majority vote of its windows. The cluster holding the larger total
talk time is the Teacher. In far-field classroom audio the embeddings are noisy
and clustering can degenerate (one cluster swallows everything); in that case a
duration heuristic overlay marks short utterances as students, which matches how
student responses actually sound in teacher-dominated Indian classrooms.
"""
import numpy as np
import torch
from faster_whisper.audio import decode_audio
from sklearn.cluster import AgglomerativeClustering

from .transcribe import Segment

SAMPLE_RATE = 16000
WINDOW_S = 2.5              # embedding window length
MIN_SEGMENTS_FOR_CLUSTERING = 4
DEGENERATE_SHARE = 0.03     # minority cluster below this share of talk time => degenerate
SHORT_UTTERANCE_S = 2.5     # heuristic: short utterances lean student
TEACHER = "teacher"
STUDENT = "student"

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from speechbrain.inference.speaker import EncoderClassifier
        except ImportError:  # older speechbrain versions
            from speechbrain.pretrained import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy

        _encoder = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="data/models/spkrec-ecapa-voxceleb",
            run_opts={"device": "cpu"},
            # COPY instead of the default SYMLINK: creating symlinks on Windows
            # requires Developer Mode / admin privileges.
            local_strategy=LocalStrategy.COPY,
        )
    return _encoder


def _segment_windows(seg: Segment, seg_index: int) -> list[tuple[int, float, float]]:
    """(segment_index, start_s, end_s) windows of ~WINDOW_S covering the segment."""
    duration = seg.end - seg.start
    n = max(1, round(duration / WINDOW_S))
    edges = np.linspace(seg.start, seg.end, n + 1)
    return [(seg_index, float(a), float(b)) for a, b in zip(edges, edges[1:])]


def _embed_windows(
    audio: np.ndarray, windows: list[tuple[int, float, float]]
) -> np.ndarray:
    encoder = _get_encoder()
    min_len = SAMPLE_RATE // 2
    embeddings = []
    batch: list[torch.Tensor] = []
    batch_size = 16
    pad_to = int(WINDOW_S * SAMPLE_RATE)

    def flush():
        nonlocal batch
        if not batch:
            return
        wavs = torch.stack(batch)
        with torch.no_grad():
            embs = encoder.encode_batch(wavs).squeeze(1).cpu().numpy()
        for e in embs:
            embeddings.append(e / (np.linalg.norm(e) + 1e-9))
        batch = []

    for _, start_s, end_s in windows:
        start = max(0, int(start_s * SAMPLE_RATE))
        end = min(len(audio), int(end_s * SAMPLE_RATE))
        chunk = audio[start:end]
        if len(chunk) < min_len:
            chunk = np.pad(chunk, (0, min_len - len(chunk)))
        if len(chunk) < pad_to:
            chunk = np.pad(chunk, (0, pad_to - len(chunk)))
        else:
            chunk = chunk[:pad_to]
        batch.append(torch.from_numpy(chunk).float())
        if len(batch) >= batch_size:
            flush()
    flush()
    return np.stack(embeddings)


def _heuristic_labels(segments: list[Segment]) -> list[str]:
    """Short utterances -> student, sustained speech -> teacher."""
    return [
        STUDENT if (s.end - s.start) < SHORT_UTTERANCE_S else TEACHER
        for s in segments
    ]


def label_speakers(audio_path: str, segments: list[Segment]) -> tuple[list[str], str]:
    """Returns (labels, method) where labels[i] is 'teacher' or 'student'."""
    if len(segments) < MIN_SEGMENTS_FOR_CLUSTERING:
        return _heuristic_labels(segments), "heuristic"
    try:
        audio = decode_audio(audio_path, sampling_rate=SAMPLE_RATE)
        windows = [w for i, seg in enumerate(segments) for w in _segment_windows(seg, i)]
        embeddings = _embed_windows(audio, windows)
        clustering = AgglomerativeClustering(
            n_clusters=2, metric="cosine", linkage="average"
        )
        window_clusters = clustering.fit_predict(embeddings)

        # Majority vote per segment (weighted by window duration)
        votes = np.zeros((len(segments), 2))
        for (seg_idx, start_s, end_s), cid in zip(windows, window_clusters):
            votes[seg_idx, int(cid)] += end_s - start_s
        seg_clusters = votes.argmax(axis=1)

        talk_time = {0: 0.0, 1: 0.0}
        for seg, cid in zip(segments, seg_clusters):
            talk_time[int(cid)] += seg.end - seg.start
        total = talk_time[0] + talk_time[1]
        teacher_cluster = max(talk_time, key=talk_time.get)
        minority_share = min(talk_time.values()) / total if total else 0.0

        labels = [
            TEACHER if int(c) == teacher_cluster else STUDENT for c in seg_clusters
        ]

        if minority_share < DEGENERATE_SHARE:
            # Clustering collapsed (noise dominates speaker identity). Overlay
            # the duration heuristic so short utterances count as students.
            heur = _heuristic_labels(segments)
            labels = [
                STUDENT if (a == STUDENT or b == STUDENT) else TEACHER
                for a, b in zip(labels, heur)
            ]
            return labels, "embedding-clustering+heuristic"
        return labels, "embedding-clustering"
    except Exception as exc:  # embedding model unavailable, corrupt audio, etc.
        print(f"[diarize] clustering failed ({exc!r}); using heuristic fallback")
        return _heuristic_labels(segments), "heuristic"
