# Meeting Transcriber

A local, modular-monolith meeting transcription application. Parts 2-3 establish a runnable Next.js dashboard, FastAPI health service, and local SQLite database; they do **not** upload media or run AI transcription.

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+

No FFmpeg or AI-model installation is required at this stage.

## Database

The backend creates SQLite tables automatically when it starts. By default, the database is stored at `storage/meeting_transcriber.db`; set `DATABASE_URL` to override it. The current schema contains `meetings` and `transcript_segments` only.

Audio extraction is started with `POST /api/meetings/{meeting_id}/extract-audio`. It runs synchronously, requires FFmpeg on `PATH`, writes 16 kHz mono PCM WAV files to `storage/audio/`, and marks the meeting `audio_ready` when successful.

Transcription is started with `POST /api/meetings/{meeting_id}/transcribe`. The meeting must be `audio_ready`. Faster-Whisper loads the configured `base` model only for that request, stores timestamped segments using `Speaker 1`, and marks a successful meeting `completed`.

Speaker diarization is started with `POST /api/meetings/{meeting_id}/diarize` after transcription completes. Create a Hugging Face access token, accept the conditions for the configured `pyannote/speaker-diarization-3.1` model, and set `PYANNOTE_AUTH_TOKEN` in your local environment. Do not commit the token. Pyannote loads only when this endpoint is requested; its results replace default speaker labels by timestamp overlap.

Run the focused database test after installing backend dependencies:

```bash
cd backend
../.venv/bin/python -m unittest discover -s tests -v
```

## Run locally

Create local configuration from the example if you need to change defaults:

```bash
cp .env.example .env
```

Start the backend in one terminal:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend exposes:

- `GET http://127.0.0.1:8000/`
- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/api/meetings/upload` (multipart field: `file`)
- OpenAPI docs at `http://127.0.0.1:8000/docs`

Uploads accept MP4, WebM, and MOV files up to 500 MB. They are stored under `storage/uploads/`, and a meeting record is created with status `uploaded`.

Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Structure

```text
frontend/        Next.js, React, TypeScript, Tailwind user interface
backend/         FastAPI service and future API/service modules
docs/            Architecture and milestone documentation
storage/         Runtime media/artifact location (ignored by Git)
test-data/       Local test fixtures (ignored by Git)
```

## Scope status

See [docs/module-status.md](docs/module-status.md) for implemented and planned modules. The architecture and roadmap remain in `docs/`.
