# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses semantic versioning for its documentation and, later, its application.

## [Unreleased]

### Planned

- Live environment installation of `frontend/node_modules`, `ffmpeg`, and AI model weights (`faster-whisper`, `pyannote.audio` with `PYANNOTE_AUTH_TOKEN`, optional `whisperx`) outside the offline sandbox.

## [1.0.0] - 2026-11-21

### Added

- Part 16 automatic `.env` / `backend/.env` file loader in `backend/app/config.py` using the Python standard library (`_load_dotenv_files()`).
- End-to-end integration test (`backend/tests/test_end_to_end_workflow.py`) verifying video upload, `202 Accepted` background processing, duplicate-job rejection (`409`), audio extraction, transcription, speaker diarization, word alignment, HTTP `Range` video streaming (`200`/`206`), and processed transcript retrieval.

### Changed

- Normalized stored `video_path` and `audio_path` values to POSIX forward slashes (`.as_posix()`) across Windows, macOS, and Linux (`backend/app/api/routes.py`).
- Allowed both `http://localhost:3000` and `http://127.0.0.1:3000` in FastAPI CORS configuration alongside `FRONTEND_ORIGIN` (`backend/app/main.py`).
- Updated `README.md` and `docs/module-status.md` with complete setup, environment, and testing instructions for all 16 milestones.

## [0.15.0] - 2026-11-21

### Added

- Part 15 upload filename sanitization (`_sanitize_upload_filename`), positive integer meeting ID validation (`400 Bad Request` on `<= 0`), and hardened `_resolve_storage_path` checks against path traversal, absolute/drive paths, null bytes, and root-directory references (`backend/app/api/routes.py`).
- Client-side file selection validation (`validateVideoFileSelection`) and single-flight request deduplication (`createSingleFlightRunner`) in `frontend/app/lib/meetings.ts`, preventing duplicate overlapping API requests during status polling and rapid dashboard refreshes.
- SQLAlchemy `selectinload` eager loading on `GET /api/meetings` to avoid N+1 segment/word queries.
- Security and validation test coverage (`test_security_filename_sanitization_storage_paths_and_meeting_ids` in `backend/tests/test_api_routes.py`).

### Changed

- Updated status polling in `frontend/app/meetings/[id]/page.tsx` to depend on `isActiveProcessing` (`[meetingId, isActiveProcessing]`) and guard in-flight polls so intervals are not recreated on same-status polls and concurrent duplicate requests are skipped.
- Allowed retrying `/diarize` and running `/align` when a meeting is in `diarization_failed` status.

## [0.14.0] - 2026-11-21

### Added

- Part 14 `POST /api/meetings/{meeting_id}/process` endpoint (`202 Accepted`) using FastAPI `BackgroundTasks` and `run_meeting_processing_pipeline` (`backend/app/api/routes.py`).
- Sequential background execution of audio extraction, Faster-Whisper transcription, pyannote speaker diarization, and optional WhisperX word alignment with per-stage SQLite status commits (`processing`, `audio_ready`, `transcribing`, `diarizing`, `aligning`, `completed`, `failed`).
- Duplicate-job prevention (`409 Conflict` when already processing), dedicated background SQLAlchemy session lifecycle (`try / finally: session.close()`), and graceful continuation when optional word alignment or gated pyannote token is unavailable.
- Frontend `"Process meeting"` trigger and status polling (`startMeetingProcessing`, `isMeetingProcessing`) in `frontend/app/lib/meetings.ts` and `frontend/app/meetings/[id]/page.tsx`.
- Background processing unit and SQLite test suite (`backend/tests/test_background_processing.py`).

### Notes

- No Celery, Redis, WebSockets, or external job queues were added.
- Individual pipeline endpoints (`/extract-audio`, `/transcribe`, `/diarize`, `/align`) remain unchanged and working.

## [0.13.0] - 2026-11-21

### Added

- Part 13 interactive transcript synchronization on `frontend/app/meetings/[id]/page.tsx` and helper functions (`ensureChronologicalSegments`, `getSegmentTimeRange`, `findActiveSegmentIndex`, `findActiveWordIndex`) in `frontend/app/lib/meetings.ts`.
- Clickable segment timestamps and aligned words that seek the HTML5 video player, live active-segment and active-word highlighting during playback (`onTimeUpdate` / `onSeeked`), and an `"Auto-scroll: On / Off"` toggle (`scrollIntoView`).
- Graceful segment-level fallback when word-level timestamps are absent and a clear empty-transcript state card.

### Notes

- Synchronization logic passed Node `--experimental-strip-types` verification across chronological ordering, boundary seeks, silence gaps, word-level vs segment-level fallback, and empty transcripts.
- Live browser playback and `next build` remain blocked until `frontend/node_modules` is installed outside the sandbox.

## [0.12.0] - 2026-11-21

### Added

- Part 12 HTTP Range video streaming endpoint `GET /api/meetings/{meeting_id}/video` (and alias `/video/stream`) supporting `200 OK`, `206 Partial Content`, `416 Range Not Satisfiable`, missing-file `404`, and path validation (`400`).
- Native responsive HTML5 `<video>` player on `frontend/app/meetings/[id]/page.tsx` with play/pause, seek bar, mute/volume controls, fullscreen toggle, retryable error state, and `getMeetingVideoUrl` / `clampSeekTime` helpers in `frontend/app/lib/meetings.ts`.
- Unit/route tests for video streaming, Range byte slicing, 416 errors, and missing-video responses (`backend/tests/test_api_routes.py`).

### Notes

- Interactive transcript click-to-seek and active playback highlighting are deferred to Part 13.
- Live browser video playback and `next build` remain blocked until `frontend/node_modules` is installed outside the sandbox.

## [0.11.0] - 2026-11-21

### Added

- Part 11 shared frontend API client and formatting utilities (`frontend/app/lib/meetings.ts`) for `GET /api/meetings`, `GET /api/meetings/{id}`, and `POST /api/meetings/upload`.
- Meeting detail route (`frontend/app/meetings/[id]/page.tsx`) displaying meeting metadata, processing status, upload date, duration, speaker/segment counts, and processed transcript segments.

### Changed

- Updated `frontend/app/page.tsx` into a responsive dashboard with an "Upload new video" trigger, loading/success/error states, automatic post-upload refresh, empty-state card, and meeting cards linking to `/meetings/[id]`.

### Notes

- Frontend `next build` requires installing npm packages (`node_modules/` is not installed in the sandboxed environment); API helper and formatting logic in `frontend/app/lib/meetings.ts` passed Node `--experimental-strip-types` checks with mocked responses.
- No transcript editing, AI summaries, search, or video playback sync was added.

## [0.10.0] - 2026-11-21

### Added

- Part 10 meeting collection and detail endpoints: `GET /api/meetings` (newest-first summary with `segment_count` and `speaker_count`) and `GET /api/meetings/{meeting_id}` (full metadata + processed transcript).
- Missing source video file guard in `POST /api/meetings/{meeting_id}/extract-audio` (`422` and `audio_failed` status).
- FastAPI OpenAPI/Swagger tag descriptions, endpoint summaries, and error response metadata across `backend/app/main.py` and `backend/app/api/routes.py`.
- Comprehensive route, error-handling, session lifecycle, and OpenAPI schema tests (`backend/tests/test_api_routes.py`).

### Changed

- Reorganized `backend/app/api/routes.py` into logical system, collection/upload, processing pipeline, and transcript retrieval sections with shared storage-path and meeting-lookup helpers.

### Notes

- Existing upload, transcription, diarization, alignment, and transcript payload shapes remain compatible with the frontend and earlier tests.
- No authentication, microservices, or background workers were added.

## [0.9.0] - 2026-11-21

### Added

- Part 9 transcript processing service (`backend/app/services/transcript.py`) for chronological ordering, consecutive same-speaker grouping, text/punctuation whitespace cleanup, `HH:MM:SS` timestamp formatting, and word-timestamp preservation.
- Updated `GET /api/meetings/{meeting_id}/transcript` and added alias `GET /api/meetings/{meeting_id}/transcript/processed` to return structured frontend-ready transcripts without modifying stored SQLite rows.
- Mocked/sample and SQLite route tests (`backend/tests/test_transcript_service.py`) covering ordering, grouping, cleaning, missing speakers, empty transcripts, and non-mutation of raw DB records.

### Notes

- No AI summaries, action items, search, background workers, or frontend UI changes were added.

## [0.8.0] - 2026-11-21

### Added

- Part 8 lazy WhisperX word-level alignment service (`backend/app/services/alignment.py`) and `TranscriptWord` database model (`transcript_words`).
- `POST /api/meetings/{meeting_id}/align` and `GET /api/meetings/{meeting_id}/transcript` endpoints with serialized word timestamps.
- `WHISPER_LANGUAGE` configuration setting (default `en`) and mocked alignment/fallback/SQLite tests (`backend/tests/test_alignment_service.py`).

### Notes

- Existing `Speaker N` labels from Part 7 and segment-level timestamps are preserved when alignment succeeds or falls back on unavailability/failure.
- `whisperx` is documented as optional rather than pinned in `backend/requirements.txt` because upstream `whisperx` conflicts with the pinned `faster-whisper==1.2.1` and `pyannote.audio==3.3.2` versions.
- No summaries, action items, or background workers were added.

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
