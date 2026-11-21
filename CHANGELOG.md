# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses semantic versioning for its documentation and, later, its application.

## [Unreleased]

### Planned

- Parts 8-16: implementation, testing, and final delivery as described in `docs/DEVELOPMENT_ROADMAP.md`.

## [0.7.0] - 2026-11-21

### Added

- Part 7 lazy pyannote.audio diarization service and `POST /api/meetings/{meeting_id}/diarize` endpoint.
- Stable anonymous labels (`Speaker 1`, `Speaker 2`, and so on) assigned by first speaker appearance.
- Timestamp-overlap speaker attribution for existing transcript segments and mocked unit/integration coverage.

### Notes

- `PYANNOTE_AUTH_TOKEN` is intentionally never stored in source control. The configured model is gated; Hugging Face model terms must be accepted before a real run.
- No word-level alignment, summaries, background workers, or frontend diarization UI was added.

## [0.6.0] - 2026-11-21

### Added

- Part 6 request-time Faster-Whisper integration using the configurable `base` CPU/int8 default.
- `POST /api/meetings/{meeting_id}/transcribe`, with `audio_ready` validation, persisted segment timestamps, `Speaker 1` labels, and status transitions.
- Mocked service and integration-test coverage for short-audio timestamps, invalid audio, and transcript persistence.

### Notes

- Models are not loaded during application startup. No diarization, word alignment, summaries, or background workers were added.
- Real Faster-Whisper installation/model download is blocked by unavailable package registry access and must be evaluated against the actual hardware.

## [0.5.0] - 2026-11-21

### Added

- Part 5 FFmpeg media service for synchronous extraction of mono, 16 kHz PCM WAV audio.
- `POST /api/meetings/{meeting_id}/extract-audio`, which records `audio_path` and transitions successful meetings to `audio_ready`.
- `audio_path` field on meetings and focused service/integration test coverage.

### Notes

- FFmpeg is not installed in the current environment, so real extraction is unavailable. No transcription, diarization, AI dependencies, or background workers were added.

## [0.4.0] - 2026-11-21

### Added

- Part 4 multipart upload endpoint at `POST /api/meetings/upload`.
- Streaming MP4, WebM, and MOV validation with a 500 MB limit, unique storage filenames, cleanup on errors, and an initial `uploaded` meeting record.
- Frontend file chooser, upload submission, and success/error feedback.
- Focused endpoint tests for successful, unsupported, empty, and oversized uploads.

### Changed

- CORS permits the frontend's required `POST` upload request.

### Notes

- The upload test suite was executed but could not import FastAPI/SQLAlchemy because dependency installation remains blocked by registry DNS. The four test cases were therefore not reached or claimed as passing. No transcription, playback, or workers were added.

## [0.3.0] - 2026-11-21

### Added

- Part 3 simple SQLite/SQLAlchemy database setup:
  - `Meeting` and `TranscriptSegment` models with a one-to-many relationship.
  - SQLite engine, session factory, and automatic startup table creation.
  - A standard-library `unittest` test for table creation and persistence/retrieval of a meeting with transcript segments.
  - `DATABASE_URL` environment configuration and README test guidance.

### Notes

- No migrations, authentication, upload functionality, or other database entities were added.
- The SQLAlchemy test was executed but is blocked by the same unavailable-PyPI DNS condition recorded for Part 2; no database test result is claimed as passing.

## [0.2.0] - 2026-11-21

### Added

- Part 2 runnable project skeleton:
  - Next.js + React + TypeScript + Tailwind static dashboard under `frontend/`.
  - FastAPI application with `GET /` and `GET /health` under `backend/`.
  - Localhost CORS configuration for the Next.js development origin.
  - Root and component-level environment examples and Git ignore rules.
  - Ignored `storage/` and `test-data/` placeholders.
  - `README.md` local run instructions and `docs/module-status.md`.

### Notes

- No upload endpoint, database, media processing, AI model, transcription, diarization, alignment, or background job was implemented.
- The Python dependencies are limited to FastAPI and Uvicorn; no AI dependencies are included.
- Dependency installation was attempted for both services. This environment could not resolve the npm or PyPI registries, so startup and endpoint smoke tests remain blocked rather than claimed as passing. See `docs/module-status.md`.

## [0.1.0] - 2026-11-20

### Added

- Part 1 project analysis and architecture documentation:
  - `docs/PROJECT_REQUIREMENTS.md`
  - `docs/SYSTEM_ARCHITECTURE.md`
  - `docs/DATABASE_DESIGN.md`
  - `docs/API_DESIGN.md`
  - `docs/FRONTEND_ARCHITECTURE.md`
  - `docs/AI_PIPELINE_DESIGN.md`
  - `docs/DEVELOPMENT_ROADMAP.md`
  - `docs/TECHNICAL_RISKS.md`
  - `docs/ARCHITECTURE_DECISIONS.md`
  - `docs/TECHNOLOGY_EVALUATION.md`
  - `docs/MILESTONE_2_CHECKLIST.md`
- Milestone 2 documentation support:
  - `docs/milestone-2/PROMPT_LOG.md`
  - `docs/milestone-2/PROMPT_ITERATION_LOG.md`
  - `docs/milestone-2/TESTING_TABLE.md`
  - `docs/milestone-2/prompts/PROMPT_01_PROJECT_ANALYSIS.md` (exact Prompt 01 archive)
- This changelog.

### Decisions

- Recommended modular monolith: Next.js frontend, FastAPI backend, SQLite + SQLAlchemy + Alembic, local filesystem storage, and a separate DB-backed worker.
- Recommended AI pipeline: WhisperX orchestration with faster-whisper ASR, pyannote.audio diarization (`speaker-diarization-community-1` primary, `3.1` fallback), and wav2vec2 forced alignment with a documented fallback ladder.
- Recorded hardware, exact ML dependency versions, diarization license choice, proxy transcoding, and public deployment/auth as unresolved.
- Confirmed only the project-brief constraints (Part 1 scope, modular monolith, no microservices/Kubernetes, anonymous speakers, no fabricated results).

### Notes

- No application code, database, API, AI model, frontend page, or test was implemented in Part 1.
- No dependency was installed.
- No test result, benchmark, accuracy metric, or team contribution is claimed.
- The workspace was empty at the start of Part 1 and is not a git repository.
- Mermaid diagrams were reviewed manually; no Mermaid renderer was installed or executed.
- The official SCSE4041 Milestone 2 seven-section titles were not provided and remain unresolved.
