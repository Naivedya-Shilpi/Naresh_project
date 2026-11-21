# Meeting Transcriber

A local, modular-monolith meeting transcription application built with Next.js (React, TypeScript, Tailwind CSS), FastAPI, SQLite/SQLAlchemy, FFmpeg, Faster-Whisper, pyannote.audio, and optional WhisperX word alignment.

## Features

1. **Video Upload & Library:** Upload MP4, WebM, and MOV recordings up to 500 MB (`POST /api/meetings/upload`) and view all meetings ordered newest-first (`GET /api/meetings`).
2. **Background & Stage-by-Stage Processing:** Trigger full asynchronous processing (`POST /api/meetings/{meeting_id}/process`, `202 Accepted`) via FastAPI `BackgroundTasks` or run individual stages (`/extract-audio`, `/transcribe`, `/diarize`, `/align`).
3. **Audio Extraction:** Converts video audio tracks to 16 kHz mono PCM WAV via FFmpeg (`storage/audio/`).
4. **Speech-to-Text & Diarization:** Uses Faster-Whisper (`base` CPU/int8 by default) for timestamped transcription and `pyannote.audio` (`pyannote/speaker-diarization-3.1`) for consistent anonymous speaker labels (`Speaker 1`, `Speaker 2`, etc.) matched by greatest timestamp overlap.
5. **Word Alignment & Fallback:** Optionally aligns word-level timestamps using WhisperX (`transcript_words`), preserving speaker labels and falling back to segment-level timestamps when WhisperX is unavailable or fails.
6. **Transcript Processing Engine:** Orders dialogue chronologically, cleans stray whitespace and punctuation spacing, merges consecutive same-speaker turns, and formats `HH:MM:SS` timestamps without overwriting raw SQLite records.
7. **Interactive Video & Transcript Player:** Streams video with HTTP `Range` support (`200 OK` / `206 Partial Content` / `416`) to a native HTML5 `<video>` player paired with clickable segment/word timestamps, live playback highlighting, and automatic transcript scrolling.

## Prerequisites

- **Python 3.11+**
- **Node.js 20+** and `npm`
- **FFmpeg** installed and available on `PATH` (`ffmpeg -version`)
- **Hugging Face access token** (`PYANNOTE_AUTH_TOKEN`) with accepted model conditions for `pyannote/speaker-diarization-3.1` (required for multi-speaker diarization; without it, background processing preserves single-speaker `Speaker 1` labels)

## Environment Configuration

Copy `.env.example` to `.env` in the project root (the backend loads `.env` and `backend/.env` automatically on startup):

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `BACKEND_HOST` | `127.0.0.1` | FastAPI bind host |
| `BACKEND_PORT` | `8000` | FastAPI bind port |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Allowed CORS frontend origin (`localhost:3000` and `127.0.0.1:3000` are both allowed) |
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | Backend base URL used by the Next.js browser client |
| `DATABASE_URL` | `sqlite:///.../storage/meeting_transcriber.db` | SQLAlchemy database connection URL |
| `WHISPER_MODEL` | `base` | Faster-Whisper model size/name |
| `WHISPER_DEVICE` | `cpu` | Faster-Whisper & WhisperX execution device (`cpu` or `cuda`) |
| `WHISPER_COMPUTE_TYPE` | `int8` | Faster-Whisper compute precision |
| `WHISPER_LANGUAGE` | `en` | Language code for optional WhisperX word alignment |
| `PYANNOTE_MODEL` | `pyannote/speaker-diarization-3.1` | Hugging Face pyannote diarization pipeline ID |
| `PYANNOTE_AUTH_TOKEN` | *(unset)* | Hugging Face access token (never commit real tokens) |

## Install and Run Locally

### 1. Start the Backend (FastAPI)

**macOS / Linux:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Swagger / OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Start the Frontend (Next.js)

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Run Tests

Run the backend unit, route, security, background-pipeline, and end-to-end workflow test suites from the project root:

**macOS / Linux:**

```bash
PYTHONPATH=backend python3 -m unittest \
  backend/tests/test_end_to_end_workflow.py \
  backend/tests/test_background_processing.py \
  backend/tests/test_api_routes.py \
  backend/tests/test_transcript_service.py \
  backend/tests/test_alignment_service.py \
  backend/tests/test_diarization_service.py \
  backend/tests/test_transcription_service.py \
  backend/tests/test_media_service.py \
  backend/tests/test_database.py -v
```

**Windows (PowerShell):**

```powershell
$env:PYTHONPATH="backend"
python -m unittest `
  backend/tests/test_end_to_end_workflow.py `
  backend/tests/test_background_processing.py `
  backend/tests/test_api_routes.py `
  backend/tests/test_transcript_service.py `
  backend/tests/test_alignment_service.py `
  backend/tests/test_diarization_service.py `
  backend/tests/test_transcription_service.py `
  backend/tests/test_media_service.py `
  backend/tests/test_database.py -v
```

## Project Structure

```text
frontend/        Next.js App Router dashboard, video player, and interactive transcript UI
backend/         FastAPI service, SQLite models, media/ASR/diarization/alignment/transcript services, and tests
docs/            Architecture, API/DB/pipeline specifications, Milestone 2 checklists, and module status
storage/         Runtime media uploads, extracted WAV audio, and SQLite database (ignored by Git)
test-data/       Local test fixtures (ignored by Git)
```

See [docs/module-status.md](docs/module-status.md) for detailed implementation and verification status across all 16 milestones.
