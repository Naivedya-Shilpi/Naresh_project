# Architecture Decision Records

| Field | Value |
|---|---|
| Document ID | ADR-001..015 |
| Version | 0.1.0 |
| Status | Part 1 decisions; recommendations require team approval |
| Last updated | 2026-11-20 |
| Related documents | `SYSTEM_ARCHITECTURE.md`, `AI_PIPELINE_DESIGN.md`, `TECHNICAL_RISKS.md` |

> **Status legend**
>
> - **CONFIRMED** - fixed by the project brief or an explicit constraint in this workspace.
> - **RECOMMENDED** - the architect's choice for the MVP, pending team approval. Not yet implemented.
> - **UNRESOLVED** - requires information or a decision that is not available in Part 1.
>
> No hardware specification is invented. No technology is described as installed or working.

---

## 1. Confirmed constraints (not technology choices)

| ID | Constraint | Source |
|---|---|---|
| C-01 | Deliver only Part 1: analysis, architecture, and documentation. | Project brief |
| C-02 | Do not implement application code or install dependencies in Part 1. | Project brief |
| C-03 | Modular monolith; avoid microservices and Kubernetes for the initial version. | Project brief |
| C-04 | Anonymous speaker labels; no real identity recognition. | Project brief |
| C-05 | Uploaded Google Meet recordings are the input; no live meeting bot. | Project brief |
| C-06 | Do not claim perfect ASR/diarization or fabricated test results. | Project brief |
| C-07 | Target hardware/GPU availability is not provided. | Workspace review |

---

## 2. Decision summary

| ADR | Decision | Status |
|---|---|---|
| 001 | Next.js + React + TypeScript + Tailwind frontend | RECOMMENDED |
| 002 | Python + FastAPI + Pydantic backend | RECOMMENDED |
| 003 | SQLite + SQLAlchemy 2.x + Alembic | RECOMMENDED |
| 004 | WhisperX orchestration with faster-whisper ASR | RECOMMENDED |
| 005 | pyannote community-1 diarization, 3.1 fallback | RECOMMENDED |
| 006 | WhisperX wav2vec2 forced alignment with fallback ladder | RECOMMENDED |
| 007 | Filesystem video/audio storage; metadata in DB | RECOMMENDED |
| 008 | Separate worker + SQLite-backed job queue | RECOMMENDED |
| 009 | REST/JSON API with multipart upload and Range streaming | RECOMMENDED |
| 010 | Local single-host environment; no Kubernetes | RECOMMENDED (details unresolved) |
| 011 | Browser-playable formats only; proxy transcoding deferred | RECOMMENDED |
| 012 | Single-user MVP without authentication | RECOMMENDED (security-scoped) |
| 013 | Normalized segment/word tables; artifacts as JSON | RECOMMENDED |
| 014 | Pin ML dependency versions; record licenses | RECOMMENDED |
| 015 | In-process pipeline stages inside the worker for MVP | RECOMMENDED |

---

## ADR-001: Frontend framework

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** Next.js (App Router), React, TypeScript, Tailwind CSS, and the native HTML5 video element.

**Alternatives considered**

- Vite + React SPA.
- Remix.
- SvelteKit.
- Vue/Nuxt.

**Reasoning:** The brief proposes Next.js. It provides file-based routing, a mature React ecosystem, TypeScript support, and a straightforward path to a local demo. The app is mostly client-interactive (upload progress, player synchronization), so React Server Components are optional rather than essential. Tailwind keeps styling local and fast to iterate for an academic timeline. The native video element is sufficient because the core requirement is seeking, playback, and time tracking.

**Advantages:** Large ecosystem, familiar to the team, easy Vercel/local deployment, good TypeScript tooling.

**Disadvantages:** Heavier than a Vite SPA; server/client component boundaries add complexity; Next.js release churn; no offline-first support.

**Unresolved concerns:** Exact Next.js/React versions; Node deployment mode; whether a same-origin proxy is used; bundle size and transcript virtualization approach.

---

## ADR-002: Backend framework

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** Python 3.11 + FastAPI + Pydantic v2, served by Uvicorn.

**Alternatives considered**

- Django + DRF.
- Flask.
- NestJS/Express.
- Litestar.

**Reasoning:** The AI stack is Python-centric (WhisperX, faster-whisper, pyannote, PyTorch). FastAPI provides typed request/response models, OpenAPI generation, async request handling, streaming responses, and a small surface area. A separate worker shares the same package and models. Django would add ORM/admin features not needed here; Flask would require more manual schema/validation work.

**Advantages:** Pydantic validation, automatic OpenAPI, async upload/streaming, Python ML integration, testability.

**Disadvantages:** CPU/GPU inference must stay out of the event loop and request process; fewer batteries-included admin features; team must manage two processes (API and worker).

**Unresolved concerns:** Exact FastAPI/Pydantic/Uvicorn versions; worker architecture in Part 14; whether to use sync or async SQLAlchemy sessions (recommend sync sessions in worker, async only where needed).

---

## ADR-003: Database

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** SQLite 3 in WAL mode with SQLAlchemy 2.x models and Alembic migrations.

**Alternatives considered**

- PostgreSQL from the start.
- MySQL/MariaDB.
- DuckDB.
- Document store.

**Reasoning:** The MVP is single-user, single-node, and read-mostly during playback. SQLite requires no service, is easy to back up, and comfortably handles tens of thousands of transcript rows. WAL plus short write transactions allows reads during worker writes. UUID text keys and standard SQL types keep a future PostgreSQL migration practical.

**Advantages:** Zero operations, fast local reads, simple demo setup, transactional integrity, Alembic support.

**Disadvantages:** Single writer; no network access; limited concurrent-write scaling; backups must be handled manually; JSON querying is limited.

**Unresolved concerns:** Retention/cleanup policy; whether multi-user auth arrives before the demo; migration timing to PostgreSQL (not MVP).

---

## ADR-004: Speech recognition model

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** Use WhisperX as the ASR orchestration layer with the faster-whisper/CTranslate2 backend. Recommended GPU default: `large-v3`, `float16`/`int8_float16`. CPU fallback: `small` or `base`, `int8`.

**Alternatives considered**

- OpenAI Whisper reference implementation.
- faster-whisper used directly.
- whisper.cpp.
- OpenAI/cloud speech API.
- Distil-Whisper.

**Reasoning:** Whisper-family models are MIT-licensed, local, multilingual, and well documented. faster-whisper is substantially faster than the reference implementation and supports CPU int8 and GPU fp16. WhisperX adds VAD batching, alignment, and diarization integration, which matches the required pipeline. A cloud API would send meeting content to a third party, add per-minute cost, and still require separate diarization.

**Advantages:** Local privacy, no per-minute API cost, multilingual, word timestamps via alignment, active open-source ecosystem.

**Disadvantages:** Model downloads are large; GPU strongly preferred; accuracy varies with audio quality; punctuation is model-dependent; hallucination is possible; WhisperX's dependency graph is fragile.

**Unresolved concerns:** Hardware/VRAM; exact model and versions; demo language(s); whether CPU-only quality is acceptable; license/attribution record.

---

## ADR-005: Diarization model

**Status:** RECOMMENDED for MVP (pending team approval and license review)

**Decision:** Use pyannote.audio with `pyannote/speaker-diarization-community-1` as the primary pipeline, accessed through WhisperX. Keep `pyannote/speaker-diarization-3.1` as a documented fallback if dependency or licensing constraints require it.

**Alternatives considered**

- NVIDIA NeMo diarization.
- Cloud diarization APIs.
- No diarization (single speaker).
- Simple energy-based speaker-change detection (insufficient).

**Reasoning:** pyannote is the established open-source diarization toolkit, integrates with WhisperX, and community-1 reports better DER than 3.1 on published benchmarks. Its exclusive diarization output simplifies word attribution. Speaker-count hints are supported. The library is MIT; community-1 weights are CC-BY-4.0 and gated, while 3.1 weights are MIT and gated.

**Advantages:** Good baseline accuracy, local execution, overlap-aware segmentation, active research, deterministic label mapping possible.

**Disadvantages:** Gated models require a Hugging Face token and terms acceptance; community-1 is CC-BY-4.0 (attribution); heavy PyTorch dependency; diarization is imperfect; overlapping speech remains hard; speaker count can be wrong.

**Unresolved concerns:** Final model/license choice; exact pyannote.audio version; offline cache strategy; whether the team accepts CC-BY-4.0 attribution.

---

## ADR-006: Alignment technology

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** Use WhisperX wav2vec2 phoneme-based forced alignment for word timestamps, with a fallback ladder: (1) forced alignment, (2) faster-whisper word timestamps, (3) segment-level timing only.

**Alternatives considered**

- Whisper's native DTW word timestamps.
- Montreal Forced Aligner (external tool).
- No word-level timing.
- Commercial alignment APIs.

**Reasoning:** WhisperX alignment is integrated with the selected ASR output, improves timestamp accuracy over DTW, and works with language-specific models. The fallback ladder prevents a missing or unsupported alignment model from failing the entire job.

**Advantages:** Better word boundaries, integrated pipeline, explicit quality flags, graceful degradation.

**Disadvantages:** Language-specific models; tokens outside the model dictionary may be unalignable; extra model download/memory; not perfect; alignment does not fix bad ASR text.

**Unresolved concerns:** Required languages and available alignment models; tolerance targets; whether to offer word-level highlighting in the MVP.

---

## ADR-007: Video and media storage

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** Store original video, WAV, artifacts, and optional proxy on the local filesystem under `storage/`; store relative paths, checksums, and metadata in SQLite. Never store large media as database blobs.

**Alternatives considered**

- SQLite BLOB storage.
- S3-compatible object storage.
- MongoDB GridFS.
- Network file share.

**Reasoning:** Video files are large, immutable, and streamed with Range requests; the filesystem is the right abstraction. Relative paths keep the deployment portable. Artifacts are regenerable and can be cleaned independently. Object storage adds credentials/network failure modes without MVP benefit.

**Advantages:** Simple, fast local streaming, easy backup/cleanup, no DB bloat, supports large files.

**Disadvantages:** No built-in replication/CDN; manual backup; local disk capacity limits; path/permission management; not multi-node.

**Unresolved concerns:** Object storage migration; retention/cleanup policy; proxy transcoding; encryption at rest for sensitive recordings.

---

## ADR-008: Background processing

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** Run a separate Python worker process that claims jobs from a SQLite `processing_jobs` table using an atomic transaction and a lease/heartbeat. Use bounded retries and stage artifacts. Do not use FastAPI `BackgroundTasks` for long jobs.

**Alternatives considered**

- FastAPI BackgroundTasks.
- Celery + Redis.
- RQ + Redis.
- Cloud queue + serverless workers.
- In-process thread pool.

**Reasoning:** Long AI jobs must survive browser disconnects and API restarts. A DB-backed queue adds no new infrastructure, is easy to demonstrate, and keeps job state observable. A single worker avoids GPU OOM and SQLite writer contention. The queue is behind an interface, so Redis/Celery can replace it later.

**Advantages:** Durable, restart-safe, minimal infrastructure, simple deployment, transparent job state.

**Disadvantages:** Polling latency; one worker by default; SQLite write contention; lease/reclaim logic must be correct; not suitable for horizontal scale.

**Unresolved concerns:** Poll interval, lease timeout, heartbeat interval, whether to add Redis when concurrent jobs are needed, graceful shutdown behavior.

---

## ADR-009: API communication

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** REST/JSON over HTTP with multipart uploads and HTTP Range video streaming. Browser calls FastAPI directly with CORS in the MVP; a Next.js rewrite/proxy is optional. Poll status every 2 seconds; defer SSE/WebSocket.

**Alternatives considered**

- GraphQL.
- tRPC.
- gRPC.
- WebSocket/SSE for progress.
- Next.js server actions for everything.

**Reasoning:** REST matches the resource model (meetings, transcripts, jobs) and is easy to test with curl/OpenAPI. Multipart and Range are native HTTP features. Polling is sufficient for processing status and avoids long-lived connection complexity. FastAPI generates OpenAPI for typed clients.

**Advantages:** Simple, debuggable, cacheable GETs, Range support, broad tooling, easy academic demonstration.

**Disadvantages:** Over/under-fetching for complex screens; polling overhead; CORS if origins differ; multiple round trips on detail pages.

**Unresolved concerns:** CORS vs same-origin proxy; whether to add SSE in Part 14; authentication scheme if deployed publicly.

---

## ADR-010: Development and deployment environment

**Status:** PARTIALLY UNRESOLVED

**Decision (recommended):** Develop and demo on a single local machine using a Python 3.11 virtual environment and a Node.js LTS runtime. Run Next.js, FastAPI, and one worker locally. Docker Compose is optional, not required. Do not use Kubernetes, serverless functions, or a cloud GPU service in the MVP.

**Alternatives considered**

- Docker Compose for reproducibility.
- Cloud VM with GPU.
- Serverless/containers for API + separate GPU worker.
- Managed transcription/diarization services.

**Reasoning:** A single-host local deployment minimizes infrastructure risk and keeps meeting data local. A lockfile and documented setup provide reproducibility. Serverless functions are a poor fit for long-running ASR and large uploads. Kubernetes is explicitly out of scope.

**Advantages:** Low cost, simple networking, local privacy, easy demonstration, fewer moving parts.

**Disadvantages:** Performance depends entirely on the host; no high availability; manual backups; environment drift between laptops; demo machine must have models cached.

**Unresolved concerns (no information provided, not assumed):**

- CPU model, core count, and RAM.
- GPU vendor/model, VRAM, CUDA/cuDNN availability.
- Available disk capacity and filesystem.
- Target OS for the demo (the current shell is macOS; this is not proof of the deployment host).
- Whether Docker is available/desired.
- Public prototype hosting and authentication.

**Recommendation:** Detect device capabilities at startup (`/capabilities`); support CPU int8 fallback; pin versions; provide a preflight script; do not hard-code GPU assumptions.

---

## ADR-011: Upload format and playback strategy

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** Accept only container/codec combinations that FFmpeg can decode **and** modern desktop browsers can play. Reject non-playable inputs with a clear error. Do not transcode a playback proxy in the MVP; keep proxy generation as a Part 5/16 enhancement if needed.

**Alternatives considered**

- Accept all FFmpeg-decodable formats and transcode every upload to H.264/AAC.
- Accept all formats and show transcript without video for unsupported codecs.
- Client-side transcoding.

**Reasoning:** The core UX requires synchronized video playback. Transcoding every upload consumes substantial CPU/disk and complicates timeline offsets. Google Meet recordings are typically MP4/H.264/AAC, so strict validation covers the primary use case.

**Advantages:** Predictable playback, no extra transcode cost, simpler timestamp mapping, clear user feedback.

**Disadvantages:** Rejects some valid recordings; MKV/HEVC users cannot play; requires browser compatibility knowledge.

**Unresolved concerns:** Exact accepted codec list; proxy implementation and storage budget; whether transcript-only mode is acceptable for rejected files.

---

## ADR-012: Authentication and user model

**Status:** RECOMMENDED with explicit security scope; public deployment UNRESOLVED

**Decision:** Ship the academic MVP as a single-user local application with no authentication. Seed one local user; keep `owner_id` in the schema. Do not expose it publicly without adding authentication and authorization.

**Alternatives considered**

- Add email/password or OAuth before the MVP.
- Anonymous sessions.
- No users table.

**Reasoning:** Authentication is not part of the product vision or the 16-part roadmap, and it would consume time needed for the AI pipeline. Keeping `owner_id` avoids a schema rewrite later. Meeting recordings are sensitive, so the security scope must be explicit.

**Advantages:** Less code, faster delivery, simpler demo.

**Disadvantages:** No isolation or access control; unsafe on a public network; sharing URLs would leak recordings.

**Unresolved concerns:** Whether the evaluator requires a hosted prototype; if so, authentication is mandatory. The API must not be deployed publicly in its current design.

---

## ADR-013: Transcript persistence model

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** Persist normalized `speakers`, `transcript_segments`, and `transcript_words` rows in SQLite. Keep raw engine outputs as versioned JSON artifacts on disk. Render SRT/VTT/text from the canonical segment model.

**Alternatives considered**

- Store the entire transcript as one JSON blob.
- Store text only with segment times.
- Use an external search engine.

**Reasoning:** Normalized rows support stable ordering, speaker filters, word-level synchronization, diagnostics, and future editing/search. JSON blobs are easy to write but hard to query and migrate. Artifacts preserve engine output without coupling the API/DB to WhisperX internals.

**Advantages:** Queryable, constraint-checked, future-proof, clean separation between raw and canonical data.

**Disadvantages:** More rows and inserts; more complex transaction; word data increases storage; migrations required.

**Unresolved concerns:** Whether to expose word-level timing in the MVP UI; retention of raw artifacts; whether transcript editing requires revision tables (future).

---

## ADR-014: Dependency pinning and licensing

**Status:** RECOMMENDED; exact versions UNRESOLVED

**Decision:** Pin exact versions of Python, Node, WhisperX, faster-whisper, CTranslate2, PyTorch, torchaudio, pyannote.audio, NumPy, and CUDA/cuDNN requirements in a lockfile before pipeline implementation. Record every model license and attribution obligation in the repository and academic report.

**Alternatives considered**

- Always install latest versions.
- Unpinned `requirements.txt`.
- Bundle model weights in the repository.

**Reasoning:** ML dependency compatibility is fragile. Unpinned installs can silently break alignment/diarization. Reproducibility is required for the academic report and demo. Model licenses affect distribution.

**Advantages:** Reproducible builds, fewer surprise breakages, auditable licenses.

**Disadvantages:** Manual security updates; platform-specific wheels; lockfile maintenance; model weights are too large to bundle.

**Unresolved concerns:** Exact versions (must be tested), CUDA version, platform wheels, whether community-1 (CC-BY-4.0) is acceptable, wav2vec2 checkpoint licenses.

---

## ADR-015: Pipeline process isolation

**Status:** RECOMMENDED for MVP (pending team approval)

**Decision:** Run pipeline stages in-process inside the dedicated worker for the MVP. Load and unload models between stages on memory-constrained hosts. Keep the engine adapters process-agnostic so a stage can move to a subprocess or remote worker later.

**Alternatives considered**

- One subprocess per stage (strong isolation, more overhead).
- Separate services per engine (rejected: microservices).
- All stages in the API process (rejected).

**Reasoning:** In-process stages are simpler to debug and share the audio/artifacts without serialization overhead. The worker is already isolated from HTTP traffic. Model unloading controls peak memory. Subprocess isolation can be added if native library crashes or OOM become frequent.

**Advantages:** Simple, fast, fewer moving parts, easy artifact reuse.

**Disadvantages:** A native crash can kill the whole job; model memory spikes; Python GIL is not a concern for GPU/native inference but affects CPU preprocessing.

**Unresolved concerns:** Whether pyannote/WhisperX native crashes require subprocess isolation; memory strategy on the actual hardware.

---

## 3. Open decisions requiring stakeholder input

| ID | Decision | Why it matters | Needed by |
|---|---|---|---|
| OD-01 | Target hardware and GPU/VRAM | Determines model size, batch size, processing time, demo feasibility | Part 2 |
| OD-02 | Exact pinned ML versions | Compatibility of WhisperX/pyannote/torch/CUDA | Part 2 |
| OD-03 | community-1 (CC-BY-4.0) vs 3.1 (MIT) | License/attribution and accuracy | Part 7 |
| OD-04 | Playback proxy for non-browser codecs | Accepts more recordings at extra CPU/storage cost | Part 5 |
| OD-05 | Public prototype hosting + auth | Privacy and academic demo requirements | Part 10 |
| OD-06 | Upload/duration caps for the demo | Disk/time budget | Part 4 |
| OD-07 | Required languages | Alignment model availability and test scope | Part 6 |
| OD-08 | Retention and deletion policy | Storage and privacy | Part 15 |

---

## 4. Decision process

- Recommendations become confirmed only after team review and, where relevant, a Part 2/6 spike.
- Any change to a confirmed decision requires a new ADR entry (or a superseding record) with date and rationale.
- Update the decision summary and `CHANGELOG.md` when status changes.
- Do not mark an ADR "accepted" merely because code exists; acceptance requires the reasoning and constraints to still hold.
