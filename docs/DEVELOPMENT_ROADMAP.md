# Development Roadmap

| Field | Value |
|---|---|
| Document ID | RMP-001 |
| Version | 0.1.0 |
| Status | Planning only - Part 1 |
| Last updated | 2026-11-20 |
| Related documents | `PROJECT_REQUIREMENTS.md`, `DEVELOPMENT_ROADMAP.md` (this file), `MILESTONE_2_CHECKLIST.md` |

> **Implementation status:** Part 1 is documentation only. Parts 2-16 are not started. Acceptance criteria below are targets; none are claimed as met unless recorded in the changelog and test evidence.

---

## 1. Roadmap principles

- Deliver a vertical slice early, then deepen AI quality.
- Keep the app runnable after every part; do not leave the main branch broken.
- Pin ML dependency versions in Part 2 and record them before writing pipeline code.
- Introduce the job-table skeleton early (Part 4) and harden background processing in Part 14.
- Do not claim a module works until its acceptance tests have run and evidence is recorded.
- Keep Part 1 documents synchronized with implementation decisions.

---

## 2. Milestone table

| Part | Objective | Primary dependencies |
|---|---|---|
| 1 | Project Analysis & Architecture | None |
| 2 | Project Initialization | 1 |
| 3 | Database Design and Implementation | 2 |
| 4 | Video Upload System | 2, 3 |
| 5 | Video and Audio Processing | 4 |
| 6 | Speech-to-Text Integration | 5 (hardware/model gate) |
| 7 | Speaker Diarization | 6 (HF token/model gate) |
| 8 | Timestamp and Word Alignment | 6, 7 |
| 9 | Transcript Processing Engine | 6, 7, 8 |
| 10 | Backend API Development | 3-9 |
| 11 | Frontend Dashboard | 10 |
| 12 | Video Player Integration | 4, 10, 11 |
| 13 | Interactive Transcript | 9, 12 |
| 14 | Background Processing | 4, 6-9 |
| 15 | Testing, Security and Optimization | All prior |
| 16 | Final Integration and Delivery | All prior |

---

## 3. Part-by-part plan

### Part 1 - Project Analysis & Architecture

- **Objective:** Establish requirements, architecture, data/API contracts, pipeline design, risks, and academic documentation.
- **Expected implementation:** Documentation only. No application code, dependencies, or database.
- **Dependencies:** None.
- **Deliverables:** Ten core documents plus the technology evaluation under `docs/`, prompt archive, Milestone 2 checklist, `CHANGELOG.md`, self-check report.
- **Acceptance criteria:** Every requested section is covered; diagrams are valid Mermaid; decisions distinguish confirmed/recommended/unresolved; no fabricated results; files verified.
- **Testing:** Documentation review and cross-file consistency check. No code tests.

### Part 2 - Project Initialization

- **Objective:** Create the runnable frontend/backend skeleton and reproducible development environment.
- **Expected implementation:** Next.js App Router + TypeScript + Tailwind scaffold; FastAPI + Pydantic v2 package; Python virtual environment and dependency lock; lint/format/typecheck configuration; `.env.example`; storage/data directories and `.gitignore`; pinned ML versions recorded after a compatibility spike; basic CI or local check script.
- **Dependencies:** Part 1.
- **Deliverables:** Runnable frontend and backend, environment documentation, pinned version record, initial test harness.
- **Acceptance criteria:** Frontend builds; backend imports and starts; lint/typecheck pass; no secrets committed; no AI models downloaded in CI; documented supported OS/Python/Node versions.
- **Testing:** Fresh-environment setup from documentation; health/smoke check; dependency installation reproducibility.

### Part 3 - Database Design and Implementation

- **Objective:** Implement the initial schema and migrations.
- **Expected implementation:** SQLAlchemy 2 models for users, meetings, videos, speakers, segments, words, jobs; Alembic initial migration; SQLite PRAGMAs; local-user seed; repository/query helpers.
- **Dependencies:** Part 2.
- **Deliverables:** Migration, models, seed, schema tests, updated `DATABASE_DESIGN.md` if implementation differs.
- **Acceptance criteria:** Upgrade/downgrade on an empty database; constraints and indexes exist; foreign keys enforced; soft-delete and active-job uniqueness tested.
- **Testing:** Migration tests, constraint tests, cascade tests, concurrent job-claim test.

### Part 4 - Video Upload System

- **Objective:** Accept, validate, store, and register uploads; create the job skeleton.
- **Expected implementation:** Streaming multipart upload, size/duration/format validation, FFprobe check, SHA-256, atomic storage, meeting/video/job transaction, upload UI, basic status read.
- **Dependencies:** Parts 2-3.
- **Deliverables:** Upload endpoint and page, storage adapter, validation tests, error mapping.
- **Acceptance criteria:** Valid MP4 accepted; oversized/corrupt/audio-only files rejected with correct codes; no partial rows/files on failure; path traversal impossible; job row created; browser shows progress.
- **Testing:** Boundary sizes, interrupted upload, unsupported codec, no audio, duplicate filenames, disk-full simulation.

### Part 5 - Video and Audio Processing

- **Objective:** Extract deterministic 16 kHz mono audio and establish timeline mapping.
- **Expected implementation:** FFprobe metadata service, FFmpeg audio extraction, offset calculation, WAV verification, artifact manifest, preprocess diagnostics, CLI/service entry point.
- **Dependencies:** Part 4.
- **Deliverables:** Media service, audio artifacts, offset tests, sample fixtures.
- **Acceptance criteria:** Extracted WAV is 16 kHz mono PCM; duration matches; offset is correct on normal and delayed-audio fixtures; failures produce stable codes; original is untouched.
- **Testing:** Codec matrix, sample rates, multiple audio streams, offset fixtures, timeout/corruption, waveform duration tolerance.

### Part 6 - Speech-to-Text Integration

- **Objective:** Produce raw transcripts with language detection and word timing where available.
- **Expected implementation:** ASR adapter (WhisperX/faster-whisper), model preflight/cache, device/compute selection, VAD/batch config, raw `asr.json`, hallucination checks, CPU/GPU smoke path.
- **Dependencies:** Part 5; hardware/model gate.
- **Deliverables:** ASR adapter, CLI run on a stored meeting, raw artifacts, model/version record, baseline WER measurement on a consented fixture.
- **Acceptance criteria:** Clean fixture transcribes; detected language recorded; empty audio handled; model failure produces a code; no API/UI integration required yet; results reproducible with pinned versions.
- **Testing:** Clean/noisy/silent fixtures, long fixture, CPU fallback, model-download failure, batch/OOM behavior, deterministic settings.

### Part 7 - Speaker Diarization

- **Objective:** Add speaker turns and stable anonymous labels.
- **Expected implementation:** pyannote adapter (community-1 primary, 3.1 fallback), HF token handling, speaker hints, raw turn artifact, degraded single-speaker mode, speaker mapping service.
- **Dependencies:** Part 6; HF token and accepted model terms.
- **Deliverables:** Diarization adapter, RTTM/JSON artifact, mapping tests, license/attribution record, DER measurement plan.
- **Acceptance criteria:** 1-5 speaker fixtures produce turns; labels map deterministically to `Speaker N`; missing token degrades explicitly; raw labels never exposed; no secrets logged.
- **Testing:** Speaker-count hints, overlap fixture, similar voices, short turns, token missing, model gating, CPU/GPU, DER on consented sample.

### Part 8 - Timestamp and Word Alignment

- **Objective:** Attach word-level timestamps and quality flags.
- **Expected implementation:** WhisperX wav2vec2 alignment, language model selection, fallback ladder, `alignment.json`, timeline offset application boundary, unaligned-token handling.
- **Dependencies:** Parts 6-7.
- **Deliverables:** Alignment adapter, quality flags, offset unit tests, synthetic sync fixture.
- **Acceptance criteria:** Words monotonic and within audio; offset applied once; unsupported language falls back with a flag; no fabricated times; sync fixture within documented tolerance.
- **Testing:** English/other language, numeric/currency tokens, model unavailable, OOM, offset fixtures, boundary/overlap cases, word/segment containment.

### Part 9 - Transcript Processing Engine

- **Objective:** Convert words, turns, and timings into readable chronological segments.
- **Expected implementation:** Speaker attribution, overlap flags, grouping thresholds, deterministic ordering, canonical transcript artifact, SRT/VTT/text renderers, invariant validation, transcript persistence service.
- **Dependencies:** Parts 6-8.
- **Deliverables:** Processing engine, renderers, fixture snapshots, invariant tests, updated design notes.
- **Acceptance criteria:** Ordering preserved; no silent text loss; segments split/merge per documented rules; unknown speakers handled; output idempotent; exports match canonical segments.
- **Testing:** Golden fixtures, tie-breaking, gaps, unaligned tokens, one speaker, overlap, duplicate chunk tokens, 4-hour synthetic scale, export snapshots.

### Part 10 - Backend API Development

- **Objective:** Expose complete REST contracts for the frontend and diagnostics.
- **Expected implementation:** All endpoints in `API_DESIGN.md`, Pydantic schemas, error envelope, pagination, status polling, Range streaming, retry, delete, jobs, health, capabilities, OpenAPI.
- **Dependencies:** Parts 3-9.
- **Deliverables:** API, OpenAPI schema, contract tests, example requests, CORS config.
- **Acceptance criteria:** Contract tests pass; Range requests return 206; error codes match; deleted/processing states correct; no filesystem paths/tokens leaked; OpenAPI generated.
- **Testing:** Endpoint contract matrix, invalid inputs, 404/409/410/413/415/416/422, Range edge cases, concurrent status reads, OpenAPI snapshot.

### Part 11 - Frontend Dashboard

- **Objective:** Provide upload, library, dashboard, and processing status UI.
- **Expected implementation:** App shell, routes, API client, TanStack Query, upload page with progress, library with filters/pagination, dashboard, status polling, error states.
- **Dependencies:** Part 10.
- **Deliverables:** Pages, components, client types, UI tests, screenshots.
- **Acceptance criteria:** Upload works end-to-end; list/detail reflect server state; polling stops; errors are actionable; responsive desktop layout; keyboard accessible.
- **Testing:** Component tests, MSW integration, upload progress, polling transitions, empty/error states, accessibility checks.

### Part 12 - Video Player Integration

- **Objective:** Play the uploaded video reliably with seeking.
- **Expected implementation:** Native HTML5 player, metadata load, Range streaming, error handling, player store, duration/current time display, source readiness.
- **Dependencies:** Parts 4, 10, 11.
- **Deliverables:** Player component, store, stream integration, browser test fixture.
- **Acceptance criteria:** Video plays in supported browsers; seeking works; duration matches API; unsupported codec shows a clear message; no full-file blob download.
- **Testing:** Range behavior, seek/pause/resume, browser matrix, missing/corrupt file, slow network simulation, memory check.

### Part 13 - Interactive Transcript

- **Objective:** Synchronize transcript reading with playback.
- **Expected implementation:** Transcript panel, timestamp buttons, active segment store/selectors, binary search, click-to-seek, auto-scroll with Follow, quality notices, accessibility, virtualization if measured necessary.
- **Dependencies:** Parts 9, 12.
- **Deliverables:** Interactive viewer, sync unit tests, E2E tests, performance notes.
- **Acceptance criteria:** Timestamp click seeks correctly; highlight matches playback; gaps handled; Follow disables on manual scroll; degraded timing works; keyboard accessible; no per-frame full-list re-render.
- **Testing:** Boundary tests, pause/seek, silence gaps, 2k+ segments, reduced motion, click-to-seek E2E, axe checks.

### Part 14 - Background Processing

- **Objective:** Make processing durable, observable, and recoverable.
- **Expected implementation:** Worker process, atomic claim/lease/heartbeat, retries/backoff, stage checkpoints/artifact reuse, progress updates, stale-job recovery, delete purge, graceful shutdown, structured logs.
- **Dependencies:** Parts 4, 6-9.
- **Deliverables:** Worker, job orchestration, recovery tests, runbook.
- **Acceptance criteria:** Upload returns immediately; jobs survive API/worker restarts; no duplicate transcripts; retries bounded; stale jobs reclaimed; purge works; progress reflects stages.
- **Testing:** Kill worker mid-stage, lease expiry, duplicate claim race, retry exhaustion, disk-full, purge failure, graceful shutdown, long-job heartbeat.

### Part 15 - Testing, Security and Optimization

- **Objective:** Verify quality, harden security, and optimize the measured bottlenecks.
- **Expected implementation:** Full unit/integration/E2E suites; WER/DER/timestamp evaluation on consented fixtures; security review (uploads, FFmpeg, paths, secrets, CORS); performance profiling; accessibility audit; documentation updates; test evidence table.
- **Dependencies:** All prior.
- **Deliverables:** Test report, quality metrics with methodology, security checklist, performance notes, updated risks, testing table with actual results.
- **Acceptance criteria:** Critical tests pass; no unresolved high-severity security issue in the MVP scope; metrics reported honestly with hardware/versions; bottlenecks measured before optimization.
- **Testing:** Full regression, adversarial uploads, secret scan, dependency audit, load smoke test, sync accuracy, accessibility, backup/restore.

### Part 16 - Final Integration and Delivery

- **Objective:** Deliver a stable demonstration and complete academic artifacts.
- **Expected implementation:** End-to-end integration, demo data, deployment/run guide, backup/restore, repository cleanup, Milestone 2 PDF inputs, 90-150 s demo reel, prompt sheets/log, working module status, contribution table.
- **Dependencies:** All prior.
- **Deliverables:** Final build, demo script/reel, repository, prototype link, documentation packet, verified test table.
- **Acceptance criteria:** Clean-machine setup works; demo flow succeeds; all claims match evidence; no secrets/large media in repo; documentation is consistent; known limitations disclosed.
- **Testing:** Full acceptance test on demo hardware, fresh-clone setup, offline model preflight, rehearsal, rollback plan.

---

## 4. Sequencing notes (no silent changes)

The 16-part numbering is retained. Two sequencing observations:

1. **Background processing is formally Part 14 but is needed earlier.** Long ASR cannot run inside an HTTP request. Mitigation: create the job table and a minimal queue in Part 4, run stages synchronously in a CLI/service during Parts 5-9, and harden the asynchronous worker in Part 14. This preserves the numbered roadmap while avoiding a late architectural rewrite.
2. **If the schedule allows, swap Part 14 before Parts 11-13.** This lets the frontend integrate against real asynchronous behavior earlier. It is a recommendation only; the official order remains unchanged unless the team explicitly approves a swap and records it in the changelog.

Other gates:

- **Hardware/model gate before Part 6:** confirm CPU/GPU, RAM/VRAM, disk, and model versions.
- **HF token gate before Part 7:** accept model terms and verify offline cache.
- **Licensing gate before Part 7:** choose community-1 (CC-BY-4.0) or 3.1 (MIT) and record attribution.
- **Codec gate before Part 4/12:** confirm browser-playable inputs or plan a proxy.

---

## 5. Definition of Done (all parts)

A part is complete only when:

1. Code is implemented and reviewed.
2. Automated tests for the new behavior pass.
3. Lint, format, and type checks pass.
4. Documentation is updated (including this roadmap's status if needed).
5. No secrets, model weights, or large media are committed.
6. Acceptance criteria are demonstrated with evidence.
7. Known limitations and unresolved issues are recorded.
8. `CHANGELOG.md` has a dated entry.

---

## 6. Academic milestone mapping

The SCSE4041 Milestone 2 requirements are tracked in `MILESTONE_2_CHECKLIST.md`. This roadmap does not assert which numbered parts correspond to the official milestone boundary; that must be confirmed against the course brief. Documentation and prompts are preserved from Part 1 onward so evidence exists regardless of the boundary.

| Academic artifact | Produced by |
|---|---|
| Architecture and requirements docs | Part 1, updated through Part 16 |
| Working prototype link | Part 16 (deployment/demo) |
| Repository link | Part 2 onward |
| 90-150 s demo reel | Part 16 |
| Prompt sheets and iteration log | Part 1 onward (append-only) |
| Testing table with actual results | Parts 4-15; finalized Part 15/16 |
| Working module status | Updated each part |
| Team contribution table | Team-provided; never inferred |
