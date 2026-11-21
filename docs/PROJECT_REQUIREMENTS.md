# Project Requirements Specification

| Field | Value |
|---|---|
| Document ID | PRD-001 |
| Project | MeetScribe (working title) |
| Version | 0.1.0 |
| Status | Draft for team review - Part 1 (architecture and documentation only) |
| Last updated | 2026-11-20 |
| Related documents | `TECHNOLOGY_EVALUATION.md`, `SYSTEM_ARCHITECTURE.md`, `AI_PIPELINE_DESIGN.md`, `DATABASE_DESIGN.md`, `API_DESIGN.md`, `FRONTEND_ARCHITECTURE.md`, `DEVELOPMENT_ROADMAP.md`, `TECHNICAL_RISKS.md`, `ARCHITECTURE_DECISIONS.md` |

> **Implementation status:** No application code, database, API, or AI pipeline exists yet. This document describes requirements for the 16-part roadmap. Nothing in this document is a claim of completed implementation or measured quality.

---

## 1. Purpose and vision

MeetScribe is a web application that accepts a recorded Google Meet video and produces a speaker-separated, timestamped transcript. The transcript is displayed next to the video player and stays synchronized with playback: timestamps are clickable, and the dialogue currently being spoken is highlighted.

The initial version uses **anonymous speaker labels** ("Speaker 1", "Speaker 2", ...). It does not identify real people. The system must be honest about the probabilistic nature of speech recognition and diarization: it must not claim perfect speaker identification or 100% transcription accuracy.

### 1.1 Product goals

1. Convert an uploaded meeting recording into a readable, chronologically ordered transcript.
2. Separate speakers consistently for the duration of a recording.
3. Provide timestamps that map to the original video timeline.
4. Make the transcript interactive: click a timestamp to seek, and highlight the active dialogue during playback.
5. Keep all processing local by default so meeting content is not sent to a third-party AI API.
6. Provide a modular architecture in which ASR, diarization, and alignment engines can be replaced independently.

### 1.2 Non-goals for the MVP

- Joining live Google Meet/Zoom/Teams calls as a bot.
- Calendar integration or automatic meeting import.
- Identifying real participant names from voice.
- Speaker enrollment or cross-meeting voice recognition.
- Real-time or streaming transcription.
- Collaborative transcript editing, comments, or sharing.
- Payments, organizations, roles, or multi-tenant administration.
- Mobile native applications.
- Production-scale cloud deployment, microservices, or Kubernetes.
- Translation, summarization, or action-item extraction.

---

## 2. Users and stakeholders

| Role | Need |
|---|---|
| End user (student/professional) | Upload a recording and read/search a synchronized transcript. |
| Project team | Build and demonstrate the system across the 16 roadmap parts. |
| Academic evaluator | Verify requirements, architecture, implementation evidence, and test results. |
| Future maintainer | Replace an AI model or storage backend without rewriting the application. |

The MVP assumes a **single local user**. Authentication and per-user data isolation are deferred, but the schema keeps an `owner_id` so multi-user support can be added without rebuilding the data model.

---

## 3. Glossary

| Term | Meaning |
|---|---|
| ASR | Automatic Speech Recognition: audio to text. |
| Diarization | Partitioning speech by speaker identity ("who spoke when"). |
| Forced alignment | Aligning known text to audio to obtain word/phone timestamps. |
| VAD | Voice Activity Detection: separating speech from silence/noise. |
| Segmentation | Grouping words into readable dialogue turns. |
| WER | Word Error Rate: transcription error metric. |
| DER | Diarization Error Rate: speaker-segmentation error metric. |
| Timeline offset | Difference between the start of the extracted audio and the start of the video presentation. |
| Job | One asynchronous processing run for a meeting. |
| Artifact | Intermediate pipeline output persisted to disk (JSON/RTTM/WAV). |

---

## 4. Scope summary

### 4.1 MVP (Parts 2-16)

- Single-user web application.
- Upload one video per meeting through the browser.
- Validate file type, size, duration, and audio stream.
- Store the original video immutably on the local filesystem.
- Extract 16 kHz mono WAV audio with FFmpeg while preserving timeline offsets.
- Transcribe with Whisper-family ASR (faster-whisper backend, orchestrated by WhisperX).
- Diarize with pyannote.audio (community-1 pipeline, with 3.1 fallback).
- Word-level alignment with WhisperX/wav2vec2 where a language model is available.
- Merge words, speakers, and timestamps into chronological segments.
- Persist transcripts in SQLite (metadata, segments, words).
- Display a meeting library, processing status, video player, and interactive transcript.
- Delete meetings and retry failed processing.
- Export transcript as JSON, SRT, VTT, or plain text (read-only export).

### 4.2 Explicitly deferred

- Authentication, authorization, sharing links, multi-tenancy.
- Resumable/chunked uploads and background uploads across sessions.
- Playback proxy transcoding for non-browser-playable codecs (see risk R-15).
- Speaker renaming, manual transcript correction, search inside meetings.
- SSE/WebSocket progress (polling is sufficient for MVP).
- Cloud object storage, PostgreSQL, Redis, Celery, GPU worker pool.

---

## 5. Functional requirements

Each module lists purpose, inputs, outputs, dependencies, MVP requirements, and future enhancements. Requirement IDs are stable and are referenced by the roadmap and tests.

### Module A - Video upload

**Purpose:** Accept a user-selected recording and persist it safely without blocking the API process.

| Aspect | Definition |
|---|---|
| Inputs | One video file from a file picker or drag-and-drop; optional title, language hint, speaker-count hints. |
| Outputs | `Meeting` row (`status=queued`), `Video` row, `ProcessingJob` row, original file on disk, HTTP `201` response. |
| Dependencies | FastAPI multipart handling, filesystem storage, FFprobe validation, database, job queue table. |

**MVP requirements**

- **FR-A-01** Provide a drag-and-drop area and a file picker. Only one file per upload in the MVP.
- **FR-A-02** Accept container/codec combinations that are both decodable by FFmpeg and playable in modern desktop browsers: MP4/MOV with H.264 + AAC, WebM with VP8/VP9 + Opus/Vorbis. MKV is accepted only if its streams are browser-playable; otherwise the upload is rejected with an actionable message. The authoritative check is FFprobe, not the file extension.
- **FR-A-03** Enforce a configurable maximum size (default 2 GiB) and maximum duration (default 4 hours). Reject oversized requests while streaming, not after buffering the whole body.
- **FR-A-04** Validate extension allowlist, declared MIME type, file signature/magic bytes where feasible, and FFprobe stream metadata. Client-supplied filename and MIME type are untrusted.
- **FR-A-05** Reject files with no audio stream, zero duration, unreadable/corrupt containers, or no browser-playable video stream. Return a specific error code; do not create a meeting row for a rejected upload.
- **FR-A-06** Write uploads to a temporary file, flush and fsync, compute SHA-256, then atomically move into the meeting's storage directory. Never derive filesystem paths from the client filename.
- **FR-A-07** Show upload progress in the browser and a clear success/failure state.
- **FR-A-08** Create the meeting, video metadata, and initial queued job in one database transaction after the file is safely stored.
- **FR-A-09** Preserve the original file unmodified for the life of the meeting.
- **FR-A-10** Default the meeting title to a sanitized filename stem; allow an optional user-supplied title.

**Future**

- Resumable/chunked uploads, upload cancellation, multi-file upload, import from URL/cloud drive, duplicate detection by checksum, pre-upload client-side duration probing.

### Module B - Audio extraction

**Purpose:** Produce a deterministic, ASR-friendly audio artifact whose timestamps can be mapped back to the original video.

| Aspect | Definition |
|---|---|
| Inputs | Validated original video, FFprobe metadata. |
| Outputs | 16 kHz, mono, 16-bit PCM WAV; audio artifact metadata including stream index and timeline offset. |
| Dependencies | FFmpeg/FFprobe, storage, job orchestration. |

**MVP requirements**

- **FR-B-01** Select the default/first audio stream deterministically and record its index, codec, sample rate, channels, and start time.
- **FR-B-02** Extract with FFmpeg to `pcm_s16le`, 16 kHz, mono, no video/subtitles/data streams.
- **FR-B-03** Never use shell interpolation; pass arguments as an argument vector.
- **FR-B-04** Compute and persist the timeline offset between the extracted audio and the video presentation (see `AI_PIPELINE_DESIGN.md`, section 6).
- **FR-B-05** Set a processing timeout and capture stderr for diagnostics.
- **FR-B-06** On extraction failure, mark the job failed with a machine-readable code and a user-safe message; retain the original file for retry.
- **FR-B-07** Verify the extracted WAV with FFprobe (duration, sample rate, channels) before starting ASR.
- **FR-B-08** Optionally apply conservative loudness normalization; do not apply aggressive denoising by default.

**Future**

- Playback proxy generation (H.264/AAC, faststart) for unsupported inputs.
- Per-participant audio tracks when multi-track recordings are available.
- Source separation for overlapping speakers; loudness normalization profiles; audio quality diagnostics.

### Module C - Speech recognition

**Purpose:** Convert speech into text with sentence-level punctuation and word-level timing where supported.

| Aspect | Definition |
|---|---|
| Inputs | Normalized WAV, language hint, model configuration. |
| Outputs | Raw ASR JSON: detected language, segments, optional words, confidence/probability fields. |
| Dependencies | WhisperX/faster-whisper, model cache, VAD, compute device selection. |

**MVP requirements**

- **FR-C-01** Transcribe using a Whisper-family model through faster-whisper, orchestrated by WhisperX. Default model is configurable; `large-v3` is the recommended GPU default and `small`/`base` are CPU fallbacks.
- **FR-C-02** Support automatic language detection and an optional user language hint. One meeting is transcribed under one detected/selected language; mixed-language meetings are best-effort.
- **FR-C-03** Preserve model-provided punctuation and casing. Do not promise punctuation quality.
- **FR-C-04** Use VAD to reduce silence processing and hallucination. Configure no-speech and compression-ratio thresholds explicitly.
- **FR-C-05** Support long recordings through batched inference and, if memory pressure requires it, overlapping window processing with global timestamp offsets. Windows must not duplicate or drop words at boundaries.
- **FR-C-06** Persist raw ASR output as a JSON artifact before downstream processing so a failed job can resume without re-transcribing.
- **FR-C-07** Record model name, revision, compute type, device, and language in artifact metadata for reproducibility.
- **FR-C-08** Detect and flag likely hallucination loops (repeated identical text over long spans) and empty/silent output.
- **FR-C-09** Do not display partial ASR output as a completed transcript.

**Future**

- Custom vocabulary/initial prompts, per-speaker language detection, translation, summarization, keyword extraction, word confidences in the UI, cloud ASR fallback.

### Module D - Speaker diarization

**Purpose:** Determine who spoke when and assign stable anonymous labels within a meeting.

| Aspect | Definition |
|---|---|
| Inputs | Normalized WAV, optional speaker-count hints, HF token and accepted model terms. |
| Outputs | Speaker turns (start, end, raw label), meeting-level speaker records, word-level speaker attribution where possible. |
| Dependencies | pyannote.audio pipeline, model cache, HF token, ASR/alignment outputs. |

**MVP requirements**

- **FR-D-01** Run a pyannote.audio diarization pipeline on the normalized audio. Default choice is `pyannote/speaker-diarization-community-1`; `pyannote/speaker-diarization-3.1` is the documented fallback if dependency or licensing constraints require it.
- **FR-D-02** Support optional `num_speakers`, `min_speakers`, and `max_speakers` hints, bounded to a safe range (default 1-10 in the UI).
- **FR-D-03** Assign display labels `Speaker 1..N` in order of first attributed speech (earliest word/turn), with deterministic tie-breaking by total speaking time and then raw label.
- **FR-D-04** Keep labels consistent for the entire recording. Raw engine labels must never leak into the UI without mapping.
- **FR-D-05** Detect speaker changes from diarization turns and map them to word/segment boundaries.
- **FR-D-06** Flag overlapping speech only when the engine exposes it. Absence of a flag means "not detected", not "no overlap".
- **FR-D-07** If diarization is unavailable (missing token, model download failure, engine error after retry), degrade explicitly: all speech under `Speaker 1`, meeting marked `diarization_status=degraded_single_speaker`, UI shows a notice. Do not silently imply multiple speakers were detected.
- **FR-D-08** Record engine name, model revision, and parameters in an artifact.

**Future**

- Real-name mapping, voiceprint enrollment across meetings, per-track diarization, overlap-aware transcription, manual speaker correction.

**Limitations to communicate in the UI and report**

Diarization is probabilistic. Similar voices, crosstalk, laughter, music, poor microphones, and distant speakers cause label errors and speaker-count errors. The system cannot guarantee correct speaker counts or attribution.

### Module E - Timestamp alignment

**Purpose:** Give each word and dialogue segment a start/end time that refers to the original video timeline.

| Aspect | Definition |
|---|---|
| Inputs | ASR output, normalized WAV, diarization turns, language code. |
| Outputs | Aligned words with start/end milliseconds, alignment quality flag, segment boundaries. |
| Dependencies | WhisperX alignment (wav2vec2), faster-whisper word timestamps fallback, timeline offset. |

**MVP requirements**

- **FR-E-01** Prefer phoneme-based forced alignment via WhisperX for word-level timestamps.
- **FR-E-02** Use a documented fallback ladder: (1) WhisperX forced alignment, (2) faster-whisper word timestamps, (3) segment-level timestamps only. Persist `alignment_quality = word | estimated_word | segment_only`.
- **FR-E-03** Never invent timestamps for tokens that cannot be aligned. Keep the token text in the segment; mark it as unaligned and let segment times cover it.
- **FR-E-04** Clamp timestamps to `[0, duration]` and enforce `start <= end`.
- **FR-E-05** Apply the audio-to-video timeline offset exactly once, at the boundary where audio-relative times become media-relative times.
- **FR-E-06** Provide segment-level start/end times even when word alignment fails.
- **FR-E-07** Validate sync on synthetic fixtures with known event times; target tolerance is documented as a test target, not a guarantee.
- **FR-E-08** Expose alignment quality in the API and UI so users do not over-trust timestamps.

**Future**

- Manual timestamp correction, confidence-based UI treatment, alignment model selection per language, drift correction using periodic anchors.

### Module F - Transcript processing

**Purpose:** Combine ASR, diarization, and alignment into readable, chronological, speaker-attributed dialogue.

| Aspect | Definition |
|---|---|
| Inputs | Aligned words, diarization turns, ASR segments, offset-corrected times. |
| Outputs | Ordered transcript segments and words ready for persistence and display. |
| Dependencies | ASR, diarization, alignment; deterministic post-processing logic. |

**MVP requirements**

- **FR-F-01** Assign each word a speaker using deterministic overlap rules; unresolved words are `UNKNOWN` or the nearest turn's speaker, with the rule recorded in the artifact.
- **FR-F-02** Sort by start time, then by original word index; never reorder speech based on speaker.
- **FR-F-03** Group words into segments on speaker change, pause threshold (default 800 ms), sentence-ending punctuation followed by a pause, or maximum duration/length thresholds.
- **FR-F-04** Preserve word order and text content. Do not drop words silently; log and count unaligned/unassigned words.
- **FR-F-05** Keep segment times covering all contained words, with a small configurable padding that never overlaps the next segment.
- **FR-F-06** Handle empty transcripts, single-speaker meetings, unknown speakers, and leading/trailing silence deterministically.
- **FR-F-07** Generate a plain-text rendering and SRT/VTT renderings from the same canonical segment model.
- **FR-F-08** Make processing idempotent: rerunning with the same artifacts produces the same segment ordering and labels.

**Future**

- Readability improvements (paragraph grouping, filler-word options), transcript editing, translations, chapter/topic segmentation, action-item extraction.

### Module G - Interactive video transcript

**Purpose:** Let the user read, navigate, and follow the meeting in sync with playback.

| Aspect | Definition |
|---|---|
| Inputs | Video stream, transcript JSON, speakers. |
| Outputs | Synchronized UI state and user interactions (seek, play, highlight, auto-scroll). |
| Dependencies | Next.js frontend, HTML5 video, Range-capable stream endpoint, transcript API. |

**MVP requirements**

- **FR-G-01** Show the video player and transcript side by side on desktop; stack them on narrow screens.
- **FR-G-02** Render each segment with speaker label, `HH:MM:SS` timestamp, and text.
- **FR-G-03** Clicking a segment timestamp seeks the video to that segment's start time and highlights the segment.
- **FR-G-04** During playback, highlight the segment whose `[start_ms, end_ms)` contains the current media time.
- **FR-G-05** Auto-scroll to the active segment by default, with a visible "Follow" toggle that turns off when the user manually scrolls.
- **FR-G-06** Seeking via the native video controls, keyboard, or timestamp click updates the highlight consistently.
- **FR-G-07** Show a clear "no transcript yet", "processing", "failed", and "degraded diarization/alignment" state.
- **FR-G-08** Use accessible buttons for timestamps and honor keyboard focus; do not make the transcript a non-semantic click target.
- **FR-G-09** Do not assume word-level timestamps exist; the UI must work with segment-level timing.

**Future**

- In-transcript search, editable transcript, speaker rename, synchronized word-level highlighting, captions track, playback speed presets beyond native controls, deep links to timestamps.

### Module H - Meeting management

**Purpose:** Provide a durable library and lifecycle for recordings and their transcripts.

| Aspect | Definition |
|---|---|
| Inputs | Upload, list, detail, status, transcript, and delete requests. |
| Outputs | Paginated meeting lists, meeting detail, status, transcript, deletion state. |
| Dependencies | Database, storage, job queue, API. |

**MVP requirements**

- **FR-H-01** List meetings with title, duration, created date, status, speaker count (when available), and a thumbnail/poster placeholder.
- **FR-H-02** Support pagination and filtering by status; sorting by newest first by default.
- **FR-H-03** Show processing stage and progress for queued/processing meetings; poll at a bounded interval.
- **FR-H-04** Show failed meetings with a safe error message and a retry action.
- **FR-H-05** Allow renaming a meeting title.
- **FR-H-06** Allow deleting a meeting. Deletion hides it immediately (soft delete), and a purge step removes files and rows. The UI must state that disk cleanup may be asynchronous.
- **FR-H-07** Provide an empty state and never display another meeting's data.
- **FR-H-08** Retain processing artifacts long enough to debug a failure, subject to a documented retention policy.

**Future**

- Folders/tags, full-text search, bulk actions, sharing links, trash/restore, storage usage dashboard, multi-user ownership.

---

## 6. Non-functional requirements

| ID | Category | Requirement | MVP target (not yet measured) |
|---|---|---|---|
| NFR-01 | Correctness | Transcript order matches speech order. | 100% ordering invariant on automated fixtures. |
| NFR-02 | Correctness | All stored times are within media duration and non-negative. | 100% enforced by validation. |
| NFR-03 | Quality | Word timestamps on clean, supported-language audio. | Target ±300 ms word boundary; validate on fixtures, do not promise. |
| NFR-04 | Quality | Segment start sync. | Target ±500 ms on clean fixtures. |
| NFR-05 | Performance | Upload of a 1 GiB file on a local network. | No full-file buffering in application memory. |
| NFR-06 | Performance | Processing speed. | Target to be benchmarked on actual hardware; no claim in Part 1. |
| NFR-07 | Reliability | Job retries on transient failure. | 3 attempts with exponential backoff; no duplicate transcripts. |
| NFR-08 | Reliability | API remains responsive during processing. | Worker runs outside the request process. |
| NFR-09 | Recovery | Restart during processing. | Job is recoverable or restartable; stage artifacts are reusable. |
| NFR-10 | Security | Untrusted uploads cannot control paths or shell commands. | Server-generated paths, argv-based FFmpeg, allowlists. |
| NFR-11 | Privacy | Default processing is local. | No third-party AI API calls in the MVP. |
| NFR-12 | Usability | Clear processing, failure, and degraded-quality states. | No false "100% accurate" claims. |
| NFR-13 | Accessibility | Keyboard-operable player and timestamp controls. | WCAG 2.1 AA target for core flows. |
| NFR-14 | Maintainability | AI engines are replaceable behind interfaces. | ASR, diarization, alignment adapters. |
| NFR-15 | Observability | Every job has structured logs and a failure code. | Request ID + job ID in logs. |
| NFR-16 | Compatibility | Latest desktop Chrome, Edge, Firefox, Safari. | Manual smoke test per release; mobile best-effort. |
| NFR-17 | Licensing | Third-party model licenses are recorded. | Attribution for CC-BY-4.0 diarization model; verify at Part 2. |
| NFR-18 | Storage | Large media never stored as database blobs. | Filesystem paths in DB only. |

---

## 7. Constraints and assumptions

### Constraints

1. Single-node, local-first deployment for the MVP.
2. SQLite is the only database; no Redis, Celery, or Kubernetes.
3. The original video is stored on a local filesystem; object storage is future work.
4. GPU availability is **unknown**. The design must support CPU-only execution with degraded speed/quality settings.
5. The system cannot guarantee perfect ASR, diarization, speaker count, or timestamp accuracy.
6. The academic timeline requires visible, honest incremental delivery across 16 parts.
7. Model downloads require internet access once; diarization requires a Hugging Face token and acceptance of gated model terms.

### Assumptions

1. Users upload completed Google Meet recordings, typically MP4 (H.264/AAC), rather than live streams.
2. Recordings contain audible speech and at most 10 active speakers in the MVP UI.
3. Recordings are at most 4 hours and 2 GiB by default; both are configurable.
4. The host has enough free disk for original video + WAV + artifacts (approximately 2.2x the video size, worst case).
5. The browser can play the uploaded container/codec; otherwise the file is rejected in the MVP.
6. A Hugging Face account and token can be provisioned before Part 7.
7. Model licenses permit academic use and distribution of results with attribution.

---

## 8. Requirement-to-roadmap traceability

| Module | Primary roadmap parts |
|---|---|
| A. Upload | 2, 3, 4, 10, 11, 15 |
| B. Audio extraction | 5, 9, 14, 15 |
| C. Speech recognition | 6, 8, 9, 14, 15 |
| D. Diarization | 7, 8, 9, 14, 15 |
| E. Alignment | 8, 9, 13, 14, 15 |
| F. Transcript processing | 9, 10, 13, 15 |
| G. Interactive UI | 11, 12, 13, 15 |
| H. Meeting management | 3, 4, 10, 11, 14, 15 |
| Non-functional | 1, 14, 15, 16 |

---

## 9. Open questions

| ID | Question | Owner | Needed by |
|---|---|---|---|
| OQ-01 | What hardware (CPU/GPU/VRAM/RAM/disk) is available for development and demonstration? | Team | Part 2 |
| OQ-02 | Which exact WhisperX, faster-whisper, pyannote.audio, PyTorch, and CUDA versions will be pinned? | Team | Part 2 |
| OQ-03 | Is the CC-BY-4.0 attribution acceptable for `speaker-diarization-community-1`, or should the MIT `3.1` pipeline be used? | Team / evaluator | Part 7 |
| OQ-04 | Will the project generate a browser-playable proxy for non-MP4 inputs, or reject them in the MVP? | Team | Part 5 |
| OQ-05 | What is the final upload size/duration cap for the demo? | Team | Part 4 |
| OQ-06 | Is authentication required for the academic demo, or is a single-user local app acceptable? | Team / evaluator | Part 10 |
| OQ-07 | What data retention period applies to uploaded recordings? | Team | Part 15 |
| OQ-08 | Which languages must be demonstrated? | Team | Part 6 |

---

## 10. Definition of MVP success

The MVP is successful when, on the team's actual hardware and with clearly documented limitations:

1. A user can upload a supported recording and see accurate processing status.
2. The system produces a chronologically ordered transcript with consistent anonymous speaker labels.
3. Every segment has a timestamp that seeks the video to the correct neighborhood.
4. Clicking timestamps and normal playback both highlight the active dialogue.
5. Failed jobs produce actionable errors and can be retried.
6. Meetings can be listed and deleted.
7. All quality claims are backed by measured test results, not assumptions.
