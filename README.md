# Classroom Voice Analytics — MVP

MakerGhat Pre-Work · Task 1. An **offline-first** prototype that turns raw classroom audio
(Hindi / English) into insights for teachers and administrators: a transcript, an approximate
teacher-vs-student separation, engagement metrics, and a plain-language classroom summary.

![Dashboard](docs/dashboard.png)

![Session view](docs/session.png)

## How it works

```
audio (mp3/wav) ──► faster-whisper (small, int8, CPU)     ──► timestamped transcript + language
                ──► SpeechBrain ECAPA speaker embeddings  ──► 2 voice clusters
                ──► CREPE neural pitch + talk time + voice consistency vote ──► which cluster is the teacher
                ──► rule-based analysis                   ──► talk time, questions, responses, silence
                ──► engagement metrics + template summary ──► JSON result
FastAPI serves the results ──► Next.js + Tailwind dashboard
```

- **Transcription** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) `small`
  multilingual model, quantized to int8 on CPU. Detects the language automatically (the provided
  recordings come out as Hindi). Everything runs locally; the models are downloaded once and cached.
- **Teacher vs student (approximate)** — each transcript segment is split into 2.5 s windows,
  each window is embedded with SpeechBrain's ECAPA-TDNN speaker-verification model, and the
  windows are clustered into 2 groups (agglomerative, cosine). Which cluster is the **teacher**
  is then decided by a vote of three independent signals, all recorded in the result JSON:
  - *talk time* — the teacher usually holds the floor longest;
  - *voice pitch* — the teacher is an adult, children's voices sit higher. Per-segment median
    F0 comes from [CREPE](https://github.com/maxrmorrison/torchcrepe), a neural pitch tracker;
  - *voice consistency* — the teacher is one voice, the students are many, so the teacher
    cluster is tighter in embedding space.

  When far-field noise collapses the clustering, short or high-pitched segments are recovered
  as student turns. Falls back to a duration heuristic for very short recordings.
- **Questions** — a teacher segment counts as a question if it ends with `?` or contains
  interrogative cues in Hindi (क्या, क्यों, कैसे, कौन, कब, कहाँ, कितना, बताओ, समझे …),
  romanized Hindi (kya, kaise, batao …) or English (what, why, how …).
- **Student responses** — a student turn starting within 5 s of the end of a teacher question.
- **Silence** — gaps longer than 2 s between speech segments.

## Engagement metrics

| Metric | Formula | Interpretation |
| --- | --- | --- |
| **Teacher Dominance Ratio** | teacher talk time ÷ total speech time | > 0.8 lecture-heavy · 0.6–0.8 teacher-led but balanced · < 0.6 highly interactive |
| **Student Participation Indicator** | student speaking turns ÷ session minutes | ≥ 1.5/min strong · 0.5–1.5 moderate · < 0.5 low participation |
| **Interaction Density** | teacher↔student speaker switches ÷ session minutes | ≥ 2/min dialogic · 0.8–2 some interaction · < 0.8 monologue-style |
| **Question–Response Rate** | questions answered within 5 s ÷ teacher questions | ≥ 60% questions are landing · 30–60% mixed uptake · < 30% largely unanswered |

Each metric is returned with its formula, explanation, and a plain-language interpretation band,
and is rendered on the session page. The session view also draws a **timeline strip** showing who
holds the floor across the hour — silences and teacher↔student exchanges are visible at a glance —
and a **"How the teacher was identified" panel** that shows each of the three signals' values for
the teacher and student clusters, whether each agreed with the outcome or abstained, and, when the
clustering collapsed, how many student turns were recovered by duration versus by pitch.

## Results on the provided recordings

All five recordings were detected as Hindi and processed end-to-end on a laptop CPU
(~6–10 min per hour of audio):

| Session | Activity | Length | Teacher talk | Questions | Answered | Reading |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-12-23 | Trumpet | 68m | 97% | 21 | 4 | lecture-heavy |
| 2026-01-28 | Trumpet | 22m | 86% | 17 | 7 | lecture-heavy |
| 2026-01-06 | Trumpet | 64m | 73% | 31 | 19 | most interactive Q&A |
| 2026-01-12 | Shadow Art | 38m | 63% | 1 | 1 | hands-on, student-driven |
| 2026-01-20 | Wind Anemometer | 60m | 98% | 1 | 0 | demonstration-style |

The spread is encouraging for the concept: activity-based sessions (Shadow Art) show markedly
lower teacher dominance than demonstrations, and questioning style differs sharply between
teachers — exactly the kind of signal administrators currently have no way to see.

## Project layout

```
backend/    FastAPI + analysis pipeline (Python 3.11)
  app/transcribe.py       faster-whisper wrapper (Silero VAD, tuned decoding)
  app/diarize.py          ECAPA embeddings → 2 clusters → three-signal teacher vote (CREPE pitch)
  app/analyze.py          questions, responses, silence, engagement metrics, summary
  app/pipeline.py         audio → result JSON
  app/main.py             FastAPI endpoints (upload, list, detail)
  scripts/preprocess.py   batch-process the provided recordings
  scripts/relabel.py      re-run speaker labelling + metrics on existing transcripts
  data/audio/             downloaded classroom recordings (gdown; not committed)
  data/results/           one JSON result per session (committed)
frontend/   Next.js (App Router) + Tailwind demo UI
  app/page.tsx                 dashboard: session cards, upload (or hosted-demo note)
  app/session/[id]/page.tsx    transcript, timeline, evidence panel, metrics, summary
  components/                  UploadCard · SessionTimeline · SpeakerEvidence · MetricCard · …
  lib/api.ts                   data source: FastAPI (dev) or public/results/ (static builds)
  scripts/sync-results.mjs     copies backend/data/results into public/results/
  public/results/              committed results the hosted demo serves
```

## Running it

**Backend** (Python 3.11):

```bash
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# one-time: download the provided classroom audio + pre-compute results
venv\Scripts\python -m gdown --folder "https://drive.google.com/drive/folders/1_WNSZFva4XPiRHlKxrhpUkrih5MiPk0D" -O data/audio
venv\Scripts\python scripts/preprocess.py

# optional: re-run speaker labelling and metrics on existing transcripts without re-transcribing
venv\Scripts\python scripts/relabel.py

# serve the API
venv\Scripts\python -m uvicorn app.main:app --port 8000
```

**Frontend**:

```bash
cd frontend
npm install
npm run dev     # http://localhost:3000  (proxies /api/* to the backend)
```

The dashboard lists the pre-processed sessions and accepts new uploads; uploads are
transcribed in a background thread and the UI polls until the analysis is ready.

## Hosting the demo

The frontend chooses its data source at build time:

- **`api`** — the default under `npm run dev`. Talks to the FastAPI backend through the
  `/api` rewrite.
- **`static`** — the default for production builds. Reads the pre-computed results committed
  under `frontend/public/results/`, so the dashboard and every session page work with no
  backend at all; the upload card becomes a note pointing here. This is what the hosted demo
  uses.

Override with `NEXT_PUBLIC_DATA_MODE=api|static`, or point a production build at a hosted
backend with `NEXT_PUBLIC_BACKEND_URL=https://…` (which also selects `api` mode).

**Deploy to Vercel:** import the GitHub repository, set **Root Directory** to `frontend`, and
deploy. No environment variables are needed. After re-processing audio, run
`npm run sync-results` inside `frontend/` and commit `public/results/` so the hosted copy
updates on the next push.

## Honest limitations (it's an MVP)

- Speaker separation is 2-cluster (teacher vs "any student") — individual students are not
  distinguished, and overlapping speech confuses both Whisper and the clustering.
- The teacher-identification vote is only as good as the clusters: when far-field noise makes
  both clusters a mix of voices, the pitch signal can disagree with the others (the session
  page shows this per recording rather than hiding it).
- Question detection is keyword/punctuation-based; rhetorical questions are counted too.
- Whisper `small` gives approximate Hindi transcripts in noisy classrooms; a larger model or
  fine-tuned Indic ASR (e.g. AI4Bharat IndicConformer) would improve accuracy.
- A student response is inferred from timing only, not from whether it answers the question.
