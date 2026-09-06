"""Classroom analysis: talk time, questions, responses, silence, engagement metrics, summary."""
import re

from .diarize import STUDENT, TEACHER
from .transcribe import Segment

RESPONSE_WINDOW_S = 5.0   # student turn starting within this window after a teacher question counts as a response
SILENCE_GAP_S = 2.0       # gaps longer than this count as silence

# Interrogative cues: Hindi (Devanagari), romanized Hindi/Hinglish, English.
QUESTION_WORDS = [
    "क्या", "क्यों", "कैसे", "कौन", "कब", "कहाँ", "कहां", "कितना", "कितने", "कितनी",
    "बताओ", "बताइए", "समझे", "समझ", "किसने", "किसका",
    "kya", "kyu", "kyun", "kaise", "kaun", "kab", "kahan", "kitna", "kitne",
    "batao", "bataiye", "samjhe", "samajh",
    "what", "why", "how", "who", "when", "where", "which",
    "can anyone", "anyone", "tell me", "right?",
]
_QUESTION_RE = re.compile(
    r"(" + "|".join(re.escape(w) for w in QUESTION_WORDS) + r")", re.IGNORECASE
)


def is_question(text: str) -> bool:
    return text.rstrip().endswith("?") or bool(_QUESTION_RE.search(text))


def merge_turns(segments: list[Segment], labels: list[str]) -> list[dict]:
    """Merge consecutive same-speaker segments into turns."""
    turns: list[dict] = []
    for seg, label in zip(segments, labels):
        if turns and turns[-1]["speaker"] == label and seg.start - turns[-1]["end"] < SILENCE_GAP_S:
            turns[-1]["end"] = seg.end
            turns[-1]["text"] += " " + seg.text
        else:
            turns.append({"speaker": label, "start": seg.start, "end": seg.end, "text": seg.text})
    return turns


def analyze(segments: list[Segment], labels: list[str], duration: float) -> dict:
    transcript = []
    for seg, label in zip(segments, labels):
        transcript.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "speaker": label,
            "text": seg.text,
            "is_question": label == TEACHER and is_question(seg.text),
        })

    teacher_time = sum(s.end - s.start for s, l in zip(segments, labels) if l == TEACHER)
    student_time = sum(s.end - s.start for s, l in zip(segments, labels) if l == STUDENT)
    total_speech = teacher_time + student_time

    turns = merge_turns(segments, labels)
    teacher_turns = [t for t in turns if t["speaker"] == TEACHER]
    student_turns = [t for t in turns if t["speaker"] == STUDENT]
    speaker_switches = sum(
        1 for a, b in zip(turns, turns[1:]) if a["speaker"] != b["speaker"]
    )

    # Teacher questions and student responses
    questions = [t for t in transcript if t["is_question"]]
    answered = 0
    for q in questions:
        if any(
            0 <= t["start"] - q["end"] <= RESPONSE_WINDOW_S
            for t in transcript
            if t["speaker"] == STUDENT
        ):
            answered += 1

    # Silence: gaps between consecutive segments
    gaps = [
        b.start - a.end for a, b in zip(segments, segments[1:]) if b.start - a.end > SILENCE_GAP_S
    ]
    if segments:
        lead_in = segments[0].start
        if lead_in > SILENCE_GAP_S:
            gaps.append(lead_in)
    silence_total = sum(gaps)
    longest_silence = max(gaps, default=0.0)

    minutes = max(duration / 60.0, 1e-6)
    dominance = teacher_time / total_speech if total_speech else 0.0
    participation_rate = len(student_turns) / minutes
    interaction_density = speaker_switches / minutes
    response_rate = answered / len(questions) if questions else 0.0

    metrics = [
        {
            "key": "teacher_dominance",
            "name": "Teacher Dominance Ratio",
            "value": round(dominance, 2),
            "display": f"{dominance:.0%}",
            "formula": "teacher talk time ÷ total speech time",
            "explanation": "Share of all speech that comes from the teacher.",
            "interpretation": (
                "Lecture-heavy: the teacher dominates the airtime; students get little room to speak."
                if dominance > 0.8 else
                "Teacher-led but balanced: mostly instruction with regular student contributions."
                if dominance > 0.6 else
                "Highly interactive: students hold a large share of the classroom talk."
            ),
        },
        {
            "key": "student_participation",
            "name": "Student Participation Indicator",
            "value": round(participation_rate, 2),
            "display": f"{participation_rate:.1f} turns/min",
            "formula": "student speaking turns ÷ session minutes",
            "explanation": "How frequently students take the floor, normalized by session length.",
            "interpretation": (
                "Strong participation: students speak up frequently."
                if participation_rate >= 1.5 else
                "Moderate participation: students contribute occasionally."
                if participation_rate >= 0.5 else
                "Low participation: students rarely speak."
            ),
        },
        {
            "key": "interaction_density",
            "name": "Interaction Density",
            "value": round(interaction_density, 2),
            "display": f"{interaction_density:.1f} switches/min",
            "formula": "teacher↔student speaker switches ÷ session minutes",
            "explanation": "How often the conversation passes between teacher and students — a proxy for back-and-forth dialogue.",
            "interpretation": (
                "Dialogic classroom: frequent back-and-forth exchange."
                if interaction_density >= 2.0 else
                "Some interaction: occasional exchanges between teacher and students."
                if interaction_density >= 0.8 else
                "Monologue-style: long uninterrupted stretches by one speaker."
            ),
        },
        {
            "key": "question_response_rate",
            "name": "Question–Response Rate",
            "value": round(response_rate, 2),
            "display": f"{response_rate:.0%}" if questions else "n/a",
            "formula": "teacher questions answered by a student within 5 s ÷ total teacher questions",
            "explanation": "How many of the teacher's questions actually draw a student response.",
            "interpretation": (
                "No questions detected in this session."
                if not questions else
                "Questions are landing: most draw a student response."
                if response_rate >= 0.6 else
                "Mixed uptake: some questions go unanswered."
                if response_rate >= 0.3 else
                "Questions largely go unanswered — they may be rhetorical or pacing may be too fast."
            ),
        },
    ]

    stats = {
        "duration_s": round(duration, 1),
        "teacher_talk_s": round(teacher_time, 1),
        "student_talk_s": round(student_time, 1),
        "teacher_talk_pct": round(100 * teacher_time / total_speech, 1) if total_speech else 0,
        "student_talk_pct": round(100 * student_time / total_speech, 1) if total_speech else 0,
        "teacher_turns": len(teacher_turns),
        "student_turns": len(student_turns),
        "teacher_questions": len(questions),
        "student_responses": answered,
        "speaker_switches": speaker_switches,
        "silence_total_s": round(silence_total, 1),
        "longest_silence_s": round(longest_silence, 1),
    }

    return {
        "transcript": transcript,
        "stats": stats,
        "metrics": metrics,
        "summary": build_summary(stats, metrics),
    }


def build_summary(stats: dict, metrics: list[dict]) -> str:
    mins = stats["duration_s"] / 60
    parts = [
        f"In this {mins:.0f}-minute session, the teacher spoke for "
        f"{stats['teacher_talk_pct']:.0f}% of the speech time and students for "
        f"{stats['student_talk_pct']:.0f}%.",
        f"Students took the floor {stats['student_turns']} times, and the conversation "
        f"switched between teacher and students {stats['speaker_switches']} times.",
    ]
    if stats["teacher_questions"]:
        parts.append(
            f"The teacher asked {stats['teacher_questions']} question"
            f"{'s' if stats['teacher_questions'] != 1 else ''}, of which "
            f"{stats['student_responses']} drew a student response."
        )
    else:
        parts.append("No teacher questions were detected.")
    if stats["silence_total_s"] > 5:
        parts.append(
            f"About {stats['silence_total_s']:.0f} s of the session was silent "
            f"(longest pause {stats['longest_silence_s']:.0f} s)."
        )
    by_key = {m["key"]: m for m in metrics}
    parts.append(by_key["teacher_dominance"]["interpretation"])
    parts.append(by_key["interaction_density"]["interpretation"])
    return " ".join(parts)
