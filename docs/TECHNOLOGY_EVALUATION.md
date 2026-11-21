# Technology Evaluation

| Field | Value |
|---|---|
| Document ID | TEV-001 |
| Version | 0.1.0 |
| Status | Part 1 evaluation - recommends, does not implement |
| Last updated | 2026-11-20 |
| Related documents | `ARCHITECTURE_DECISIONS.md`, `AI_PIPELINE_DESIGN.md`, `SYSTEM_ARCHITECTURE.md` |

> **Scope and honesty:** This document evaluates the requested stack and recommends an MVP combination. It does not claim that any component is installed or benchmarked in this project. Hardware specifications for the team's machine are unknown and are not assumed. Vendor claims are labelled as vendor claims. Licensing was checked against public sources on 2026-11-20 and must be re-verified at Part 2.

---

## 1. Evaluation criteria

| Criterion | What is assessed |
|---|---|
| Fit | Does it satisfy the required workflow (upload, transcribe, diarize, align, synchronize)? |
| Accuracy | Known strengths/limitations for meeting speech, not a guarantee. |
| Performance | CPU/GPU behavior, batching, memory, long-audio handling. |
| Integration | Compatibility with the rest of the pipeline and API. |
| Installation | Dependency complexity, platform/wheel support, model gating. |
| Licensing | Code and model licenses, attribution, distribution constraints. |
| API key | Whether a paid API or gated model token is required. |
| Operability | Local execution, observability, replaceability, maintenance. |

---

## 2. Stack recommendation summary

| Layer | Recommended for MVP | Alternatives considered | Status |
|---|---|---|---|
| Frontend | Next.js App Router + React + TypeScript + Tailwind + native HTML5 video | Vite SPA, Remix, SvelteKit | Recommended |
| Backend | Python 3.11 + FastAPI + Pydantic v2 | Django/DRF, Flask, NestJS | Recommended |
| Database | SQLite + SQLAlchemy 2 + Alembic | PostgreSQL, MySQL, DuckDB | Recommended |
| Media | FFmpeg + FFprobe | PyAV, GStreamer, MediaInfo | Recommended |
| ASR | WhisperX orchestration + faster-whisper/CTranslate2 | OpenAI Whisper, whisper.cpp, cloud API | Recommended |
| Diarization | pyannote.audio community-1 (3.1 fallback) | NeMo, cloud diarization, no diarization | Recommended |
| Alignment | WhisperX wav2vec2 forced alignment | Whisper DTW, MFA, segment-only | Recommended |
| Storage | Local filesystem for media; SQLite for metadata/transcript | Object storage, DB BLOBs | Recommended |
| Queue | SQLite job table + dedicated worker | FastAPI BackgroundTasks, Celery/Redis | Recommended |

Detailed reasoning is in `ARCHITECTURE_DECISIONS.md` (ADR-001..015). This document focuses on the AI/media evaluation requested by the brief.

---

## 3. Speech recognition and diarization technologies

### 3.1 OpenAI Whisper

| Aspect | Evaluation |
|---|---|
| Purpose | General-purpose open-source speech recognition; multilingual transcription and translation. |
| Architecture | Encoder-decoder Transformer trained on weakly supervised audio-text pairs; log-mel spectrogram input; multitask tokens; processes audio in 30-second windows. |
| Advantages | MIT-licensed code and weights; broad language coverage; robust to many recording conditions; simple reference implementation; large community. |
| Disadvantages | Slow relative to optimized runtimes; high memory for larger models; timestamps are segment-level or DTW-based and can be inaccurate; no diarization; can hallucinate on silence/noise; no native batching in the reference implementation. |
| Hardware requirements | CPU possible but slow; GPU strongly preferred for larger models. Model sizes range from tiny to large-v3; larger models need more RAM/VRAM. Exact requirements depend on model, precision, and batch size. |
| CPU/GPU | Both; PyTorch backend. CUDA GPU accelerates substantially. Apple Silicon support depends on the PyTorch build and is not assumed. |
| Installation complexity | Moderate: Python, PyTorch, FFmpeg; platform-specific wheels. |
| Licensing | MIT (code and model weights). |
| API key | None for local weights. The separate OpenAI hosted transcription API requires a key and sends audio to a third party; not proposed for the MVP. |
| Suitability | Good reference/fallback, but not the primary MVP engine because of speed and timestamp limitations. |

### 3.2 Faster-Whisper

| Aspect | Evaluation |
|---|---|
| Purpose | Faster inference of Whisper models using CTranslate2. |
| Architecture | Whisper weights converted to CTranslate2; optimized CPU/GPU kernels; 8-bit quantization; optional batched inference and Silero VAD; optional word timestamps. |
| Advantages | The project reports up to about 4x speedup over the reference implementation for the same accuracy, with lower memory; int8 CPU support; fp16 GPU support; word timestamps; VAD integration; MIT license. |
| Disadvantages | Not a diarization system; no phoneme-level forced alignment; GPU requires compatible CUDA/cuBLAS/cuDNN libraries; model conversion/version compatibility; accuracy still inherits Whisper limitations. |
| Hardware requirements | CPU works with int8 and smaller models; GPU improves throughput. Memory scales with model size, precision, batch size, and audio length. |
| CPU/GPU | Both; CTranslate2 GPU support is CUDA-oriented. CPU int8 is the practical fallback. |
| Installation complexity | Moderate: `pip install faster-whisper`; GPU needs NVIDIA libraries. The project notes current CTranslate2 CUDA 12 + cuDNN 9 requirements and older-version workarounds. |
| Licensing | MIT. |
| API key | None. |
| Suitability | The ASR inference engine for the MVP, used through WhisperX. |

### 3.3 WhisperX

| Aspect | Evaluation |
|---|---|
| Purpose | Pipeline layer for fast long-form transcription, word-level timestamps, and speaker diarization integration. |
| Architecture | Silero VAD + batched faster-whisper transcription + language-specific wav2vec2 forced alignment + pyannote diarization + word-speaker assignment. |
| Advantages | Closest open-source match to the required pipeline; word-level timing; batched long-audio inference; speaker integration; BSD-2-Clause code license; active project. |
| Disadvantages | Fragile ML dependency graph; language-specific alignment models; tokens outside the alignment dictionary may be untimed; overlapping speech is poorly handled; diarization is imperfect; gated HF models; release/version churn; not a turnkey accuracy guarantee. |
| Hardware requirements | CPU or GPU; GPU strongly recommended for large models and long recordings. Memory is needed for ASR, alignment, and diarization models. The project documents reducing batch size/model size/compute type to lower memory. |
| CPU/GPU | Both. CPU command path uses `--compute_type int8`; GPU uses CUDA with fp16/int8 variants. Apple Silicon is typically CPU-only for CTranslate2; verify on the actual machine. |
| Installation complexity | High: Python, PyTorch, torchaudio, faster-whisper/CTranslate2, pyannote.audio, CUDA/cuDNN, alignment models, FFmpeg. Pin versions. |
| Licensing | WhisperX code: BSD-2-Clause. Whisper weights: MIT. pyannote models: varying (community-1 CC-BY-4.0; 3.1 MIT), gated. Alignment checkpoints: verify each model card. |
| API key | No inference API key for local execution. A Hugging Face token is required to download gated pyannote models; the user must accept the model terms. |
| Suitability | Recommended MVP orchestrator, behind `ASREngine`, `DiarizationEngine`, and `AlignmentEngine` adapters. |

WhisperX's own documentation states that overlapping speech is not handled particularly well, diarization is "far from perfect", and words outside the alignment model's dictionary are not given timings. Those limitations are carried into this project and must be disclosed in the UI/report.

### 3.4 pyannote.audio

| Aspect | Evaluation |
|---|---|
| Purpose | Speaker diarization (who spoke when), voice activity detection, segmentation, and speaker embeddings. |
| Architecture | Neural speaker segmentation (powerset multi-class) + speaker embedding + clustering; pipeline API exposes speaker turns; community-1 adds exclusive diarization for easier reconciliation with transcripts. |
| Advantages | Established open-source diarization toolkit; local execution; exclusive diarization output; speaker-count hints; better published DER for community-1 than 3.1; integrates with WhisperX. |
| Disadvantages | Gated models and HF token; heavy PyTorch dependency; DER still far from zero; overlap and similar voices cause errors; speaker count can be wrong; turn boundaries are approximate. |
| Hardware requirements | CPU works but is slow; GPU recommended for long recordings. Memory depends on model and audio duration. |
| CPU/GPU | Both; pipelines run on CPU by default and can be moved to CUDA. |
| Installation complexity | Moderate to high: PyTorch/torchaudio, pyannote.audio, model downloads, HF authentication, version compatibility with WhisperX. |
| Licensing | Library: MIT. `speaker-diarization-community-1` weights: CC-BY-4.0, gated, attribution required. `speaker-diarization-3.1`: MIT, gated, with related model conditions. |
| API key | Hugging Face access token plus acceptance of model conditions. No paid inference key is required for local use. Optional pyannoteAI cloud keys are not part of the MVP. |
| Suitability | The diarization engine for the MVP, with community-1 primary and 3.1 fallback. |

### 3.5 Compatibility assessment

| Combination | Assessment |
|---|---|
| Whisper + faster-whisper | Good: faster-whisper consumes converted Whisper weights; pin CTranslate2 and model versions. |
| WhisperX + faster-whisper | Good by design: WhisperX uses faster-whisper as its backend; version compatibility must be pinned. |
| WhisperX + pyannote community-1 | Requires a current WhisperX/pyannote.audio combination and an HF token; community-1 is the current documented path. |
| WhisperX + pyannote 3.1 | Older documented path; often requires older pyannote.audio/WhisperX pins. Choose one path deliberately. |
| WhisperX + wav2vec2 alignment | Language-specific model required; unsupported languages need a fallback. |
| Faster-whisper + pyannote directly | Viable fallback without WhisperX, but requires custom word-speaker reconciliation and alignment orchestration. |
| CUDA 12 + CTranslate2 | Requires compatible cuBLAS/cuDNN; verify the exact versions on the target machine. |
| Python 3.12 + ML stack | Possible but riskier for wheel availability; Python 3.11 is the safer default pending a Part 2 spike. |

**Critical conclusion:** These components do not automatically produce perfectly synchronized, speaker-correct transcripts. Compatibility is a version-pinning problem, and correctness requires explicit reconciliation, timeline mapping, fallback ladders, and evaluation.

---

## 4. FFmpeg evaluation

### 4.1 Purpose in this project

| Task | How FFmpeg/FFprobe is used |
|---|---|
| Video metadata extraction | `ffprobe -print_format json -show_format -show_streams` for duration, codecs, dimensions, sample rate, channels, start times. |
| Audio extraction | Select the default audio stream, drop video/subtitles/data, write PCM WAV. |
| Audio format conversion | Decode AAC/Opus/MP3/etc. to PCM; no video transcoding in the MVP. |
| Sample rate conversion | Resample to 16 kHz mono for Whisper/pyannote. |
| Audio preprocessing | Optional loudness normalization/high-pass; VAD is handled by the ASR/diarization stack, not by FFmpeg filters. |
| Playback proxy (future) | H.264/AAC MP4 with faststart for non-browser-playable inputs; not MVP by default. |

Recommended extraction shape (argument vector, no shell):

```text
ffmpeg -hide_banner -nostdin -i <input> \
  -map 0:a:<index> -vn -sn -dn \
  -ac 1 -ar 16000 -c:a pcm_s16le \
  -y <output.wav>
```

The exact command is implemented and tested in Part 5. No `-copyts`; the timeline offset is derived from FFprobe metadata (see `AI_PIPELINE_DESIGN.md`, section 6).

### 4.2 Advantages and disadvantages

| Aspect | Evaluation |
|---|---|
| Advantages | Ubiquitous; decodes almost every container/codec; precise probing; deterministic CLI; works on CPU; no API key; easy automation; supports loudness filters. |
| Disadvantages | CLI error handling and progress parsing are awkward; builds differ in codec support; licensing depends on build flags; malformed media can crash/hang a process; timestamp/edit-list behavior is subtle; no native diarization. |
| Hardware | CPU-bound for audio extraction; no GPU required. Video proxy transcoding would be CPU/GPU-intensive and is deferred. |
| CPU/GPU | CPU for audio; optional hardware encoders only if a proxy is added later. |
| Installation complexity | Low to moderate: package manager or static build; verify codecs and license. |
| Licensing | FFmpeg is LGPL-2.1-or-later by default, but GPL applies if built with GPL components (for example x264). Distribution must comply with the chosen build. |
| API key | None. |
| Suitability | Essential for the MVP. Use FFprobe as the validation/metadata authority and FFmpeg for extraction. |

**Risks:** command injection (mitigated by argv), path traversal (server paths), no-audio/corrupt inputs, timeouts, disk-full, and timeline offsets from edit lists. Tests must include these cases.

---

## 5. Storage evaluation and recommendation

| Data | Recommended storage | Format | Rationale |
|---|---|---|---|
| Original video | `storage/originals/{meeting_id}/source{ext}` | Original bytes | Immutable, streamed with Range, too large for SQLite. |
| Extracted audio | `storage/audio/{meeting_id}/audio_16k_mono.wav` | 16 kHz mono PCM WAV | Deterministic input for ASR/diarization; regenerable. |
| Transcript | SQLite `speakers`, `transcript_segments`, `transcript_words` | Normalized rows | Queryable, ordered, constraint-checked, supports sync. |
| Raw engine output | `storage/artifacts/{meeting_id}/{job_id}/*.json` | Versioned JSON/RTTM | Debuggable, reusable on resume, decoupled from DB schema. |
| Temporary files | `storage/tmp/{job_id}/` | Any | Cleaned after success/failure; prevents partial files in final paths. |
| Model cache | `storage/models/` / `HF_HOME` | Model-specific | Large, shared, not tied to a meeting; excluded from repo/backups. |
| Playback proxy (future) | `storage/playback/{meeting_id}/proxy.mp4` | H.264/AAC | Only if non-browser inputs must be supported. |

**Recommendation:** Filesystem for media and artifacts; SQLite for metadata and canonical transcript; relative paths in DB; no large BLOBs; atomic writes; quota/capacity checks; purge on deletion; backups for the DB and original media according to the retention policy.

**Alternatives rejected for the MVP:** SQLite BLOBs (bloat, slow streaming, backup cost), object storage (extra credentials/network, unnecessary for single-host), and storing raw JSON transcripts only (hard to query/migrate).

---

## 6. Recommended MVP combination

**Application stack:** Next.js App Router + React + TypeScript + Tailwind; FastAPI + Pydantic; SQLite + SQLAlchemy + Alembic; local filesystem storage; DB-backed worker.

**AI/media stack:**

1. FFprobe validates and probes the upload.
2. FFmpeg extracts 16 kHz mono PCM WAV.
3. WhisperX with faster-whisper (`large-v3` on GPU; `small`/`base` int8 on CPU) transcribes.
4. WhisperX wav2vec2 aligns words; fallback to faster-whisper word times or segment-only.
5. pyannote community-1 (or 3.1) diarizes.
6. Deterministic reconciliation assigns `Speaker N`, groups segments, applies the timeline offset once, and persists.

**Conditions before implementation:**

- Confirm actual CPU/GPU/RAM/disk.
- Pin exact versions and run a compatibility spike (Part 2).
- Accept gated model terms and pre-cache weights.
- Confirm the community-1 CC-BY-4.0 attribution or choose 3.1.
- Define language scope and test fixtures.
- Measure WER/DER/timestamp error before making any quality claim.

---

## 7. Public sources checked (2026-11-20)

| Source | Used for |
|---|---|
| `https://github.com/m-bain/whisperX` (README, LICENSE) | Pipeline features, limitations, diarization requirements, BSD-2 license. |
| `https://github.com/SYSTRAN/faster-whisper` (README) | CTranslate2 architecture, performance claims, CUDA/cuDNN requirements, MIT license. |
| `https://huggingface.co/pyannote/speaker-diarization-community-1` | CC-BY-4.0 license, gating, exclusive diarization, benchmark context. |
| `https://huggingface.co/pyannote/speaker-diarization-3.1` | MIT license, gating, pyannote.audio >=3.1 requirement, speaker hints. |
| `https://github.com/openai/whisper` | MIT license and reference architecture (well-known project documentation). |
| `https://ffmpeg.org/legal.html` | FFmpeg LGPL/GPL licensing overview. |

Documentation changes over time. Re-verify licenses and commands at Part 2 and before final submission. Do not treat vendor benchmarks as this project's measurements.
