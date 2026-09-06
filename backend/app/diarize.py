"""Approximate teacher/student separation.

1. Every transcript segment is split into 2.5 s windows, each window is embedded
   with SpeechBrain ECAPA-TDNN, and the windows are clustered into 2 groups
   (agglomerative, cosine). A segment takes the duration-weighted majority
   cluster of its windows.

2. Which cluster is the teacher is decided by a vote of three independent
   signals, each recorded in the result so the decision is auditable:
     talk time         the teacher usually holds the floor longest
     pitch (F0)        the teacher is an adult; children's voices sit higher.
                       Per-segment median F0 from the CREPE neural pitch tracker.
     voice consistency the teacher is one voice, the students are many, so the
                       teacher cluster is tighter in embedding space.
   Pitch and consistency abstain when either cluster has fewer than 3 segments:
   a one- or two-segment cluster is trivially tight and its pitch is a single
   noisy reading, so only talk time can judge it.

3. Far-field classroom noise can collapse the clustering (one cluster swallows
   nearly everything). When the minority cluster holds < 3 % of talk time two
   per-segment overlays recover student turns: short utterances lean student,
   and anything pitched well above the teacher's median F0 is a student.
"""
import numpy as np
import torch
from faster_whisper.audio import decode_audio
from sklearn.cluster import AgglomerativeClustering

from .transcribe import Segment

SAMPLE_RATE = 16000
WINDOW_S = 2.5               # embedding window length
MIN_SEGMENTS_FOR_CLUSTERING = 4
MIN_CLUSTER_SEGMENTS = 3     # pitch/consistency abstain if a cluster is smaller than this
DEGENERATE_SHARE = 0.03      # minority cluster below this share of talk time => degenerate
SHORT_UTTERANCE_S = 2.5      # overlay: short utterances lean student
PITCH_RATIO_STUDENT = 1.35   # overlay: F0 this far above the teacher's median => student (~5 semitones)
F0_MAX_S = 6.0               # pitch is estimated on at most this much of each segment
F0_HOP = 320                 # 20 ms at 16 kHz
F0_MIN_VOICED_FRAMES = 5
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


def _segment_pitch(audio: np.ndarray, segments: list[Segment]) -> np.ndarray:
    """Median voiced F0 (Hz) per segment via CREPE; NaN where nothing voiced was found."""
    import torchcrepe

    f0s = np.full(len(segments), np.nan)
    max_len = int(F0_MAX_S * SAMPLE_RATE)
    for i, seg in enumerate(segments):
        start = max(0, int(seg.start * SAMPLE_RATE))
        end = min(len(audio), int(seg.end * SAMPLE_RATE), start + max_len)
        chunk = audio[start:end]
        if len(chunk) < SAMPLE_RATE // 4:
            continue
        wav = torch.from_numpy(chunk).float().unsqueeze(0)
        with torch.no_grad():
            f0, periodicity = torchcrepe.predict(
                wav, SAMPLE_RATE, hop_length=F0_HOP, fmin=60.0, fmax=500.0,
                model="tiny", return_periodicity=True, device="cpu", batch_size=512,
            )
        voiced = f0[periodicity > 0.5]
        if voiced.numel() >= F0_MIN_VOICED_FRAMES:
            f0s[i] = float(voiced.median())
    return f0s


def _heuristic_labels(segments: list[Segment]) -> list[str]:
    """Short utterances -> student, sustained speech -> teacher."""
    return [
        STUDENT if (s.end - s.start) < SHORT_UTTERANCE_S else TEACHER
        for s in segments
    ]


def _pick_teacher(
    segments: list[Segment],
    seg_clusters: np.ndarray,
    windows: list[tuple[int, float, float]],
    window_clusters: np.ndarray,
    embeddings: np.ndarray,
    f0s: np.ndarray,
) -> tuple[int, dict]:
    """Vote across talk time, pitch and voice consistency. Returns (cluster_id, evidence)."""
    talk = np.zeros(2)
    for seg, c in zip(segments, seg_clusters):
        talk[int(c)] += seg.end - seg.start

    pitch = np.full(2, np.nan)
    for c in (0, 1):
        vals = f0s[(seg_clusters == c) & ~np.isnan(f0s)]
        if len(vals):
            pitch[c] = float(np.median(vals))

    dispersion = np.full(2, np.nan)
    for c in (0, 1):
        embs = embeddings[window_clusters == c]
        if len(embs) >= 2:
            centroid = embs.mean(axis=0)
            centroid /= np.linalg.norm(centroid) + 1e-9
            dispersion[c] = float(np.mean(1.0 - embs @ centroid))

    # A cluster of one or two segments is trivially tight and its pitch is a
    # single noisy reading, so pitch and consistency cannot judge it; only talk
    # time votes, and the per-segment overlay recovers students afterwards.
    n_seg = np.bincount(seg_clusters.astype(int), minlength=2)
    too_small = int(n_seg.min()) < MIN_CLUSTER_SEGMENTS
    votes: dict[str, int | None] = {
        "talk_time": int(np.argmax(talk)),
        "pitch": None if too_small or np.isnan(pitch).any() else int(np.argmin(pitch)),
        "voice_consistency": None
        if too_small or np.isnan(dispersion).any()
        else int(np.argmin(dispersion)),
    }
    tally = [0, 0]
    for v in votes.values():
        if v is not None:
            tally[v] += 1
    teacher = int(np.argmax(tally)) if tally[0] != tally[1] else votes["talk_time"]

    def signal(name: str, values: np.ndarray, unit: str) -> dict:
        s = 1 - teacher
        return {
            "name": name,
            "unit": unit,
            "teacher": None if np.isnan(values[teacher]) else round(float(values[teacher]), 2),
            "student": None if np.isnan(values[s]) else round(float(values[s]), 2),
            "agrees": votes[name] == teacher if votes[name] is not None else None,
        }

    evidence = {
        "votes_for_teacher": tally[teacher],
        "votes_cast": sum(v is not None for v in votes.values()),
        "signals": [
            signal("talk_time", talk, "s"),
            signal("pitch", pitch, "Hz"),
            signal("voice_consistency", dispersion, "dispersion"),
        ],
    }
    if too_small:
        evidence["note"] = (
            f"the smaller cluster has only {int(n_seg.min())} segment(s), too few for "
            "pitch or consistency to judge; talk time decided"
        )
    return teacher, evidence


def label_speakers(
    audio_path: str, segments: list[Segment]
) -> tuple[list[str], str, dict | None]:
    """Returns (labels, method, evidence); labels[i] is 'teacher' or 'student'."""
    if len(segments) < MIN_SEGMENTS_FOR_CLUSTERING:
        return _heuristic_labels(segments), "heuristic", None
    try:
        audio = decode_audio(audio_path, sampling_rate=SAMPLE_RATE)
        windows = [w for i, seg in enumerate(segments) for w in _segment_windows(seg, i)]
        embeddings = _embed_windows(audio, windows)
        window_clusters = AgglomerativeClustering(
            n_clusters=2, metric="cosine", linkage="average"
        ).fit_predict(embeddings)

        votes = np.zeros((len(segments), 2))
        for (seg_idx, start_s, end_s), cid in zip(windows, window_clusters):
            votes[seg_idx, int(cid)] += end_s - start_s
        seg_clusters = votes.argmax(axis=1)

        try:
            f0s = _segment_pitch(audio, segments)
        except Exception as exc:  # torchcrepe missing or failed: vote without pitch
            print(f"[diarize] pitch estimation failed ({exc!r}); voting without pitch")
            f0s = np.full(len(segments), np.nan)

        teacher_cluster, evidence = _pick_teacher(
            segments, seg_clusters, windows, window_clusters, embeddings, f0s
        )
        labels = [TEACHER if int(c) == teacher_cluster else STUDENT for c in seg_clusters]

        talk = np.zeros(2)
        for seg, c in zip(segments, seg_clusters):
            talk[int(c)] += seg.end - seg.start
        minority_share = talk.min() / talk.sum() if talk.sum() else 0.0
        method = "embedding-clustering+pitch-vote"

        if minority_share < DEGENERATE_SHARE:
            # Clustering collapsed: recover student turns from per-segment cues.
            teacher_f0 = evidence["signals"][1]["teacher"]
            heur = _heuristic_labels(segments)
            short_only = pitch_only = both = 0
            for i in range(len(segments)):
                if labels[i] != TEACHER:
                    continue
                short = heur[i] == STUDENT
                high_pitched = (
                    teacher_f0 is not None
                    and not np.isnan(f0s[i])
                    and f0s[i] > PITCH_RATIO_STUDENT * teacher_f0
                )
                if short or high_pitched:
                    labels[i] = STUDENT
                    if short and high_pitched:
                        both += 1
                    elif short:
                        short_only += 1
                    else:
                        pitch_only += 1
            evidence["degenerate_overlay"] = {
                "minority_share": round(float(minority_share), 4),
                "segments_relabelled_student": short_only + pitch_only + both,
                "by_short_duration_only": short_only,
                "by_high_pitch_only": pitch_only,
                "by_both": both,
                "teacher_median_f0_hz": teacher_f0,
            }
            method += "+overlay"
        return labels, method, evidence
    except Exception as exc:  # embedding model unavailable, corrupt audio, etc.
        print(f"[diarize] clustering failed ({exc!r}); using heuristic fallback")
        return _heuristic_labels(segments), "heuristic", None
