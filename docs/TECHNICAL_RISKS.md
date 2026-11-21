# Technical Risks

| Field | Value |
|---|---|
| Document ID | RSK-001 |
| Version | 0.1.0 |
| Status | Initial risk register - Part 1 |
| Last updated | 2026-11-20 |
| Related documents | `AI_PIPELINE_DESIGN.md`, `ARCHITECTURE_DECISIONS.md`, `DEVELOPMENT_ROADMAP.md` |

> **No fabricated measurements.** Probability and impact ratings below are engineering judgments for planning, not observed statistics. No risk has been "validated" or "mitigated" in code because no implementation exists yet. Ratings must be revisited after Part 5/6 benchmarks and Part 15 testing.

---

## 1. Rating definitions

| Rating | Probability | Impact |
|---|---|---|
| High | Expected to occur during the MVP without action (>50%) | Critical: blocks the demo, loses data, or invalidates the core workflow |
| Medium | Plausible (roughly 15-50%) | High: major feature degradation or significant rework |
| Low | Unlikely (<15%) | Medium: workaround exists; Low: cosmetic/minor |

---

## 2. Risk register

| ID | Risk and description | P | I | Mitigation | Fallback |
|---|---|---|---|---|---|
| R-01 | **Poor recording quality.** Noise, echo, clipping, low volume, distant microphones, or music reduce ASR and diarization accuracy. | High | High | User guidance; audio diagnostics (peak, clipping, RMS); VAD thresholds; quality warnings; evaluate on noisy fixtures. | Show a low-quality warning; deliver best-effort transcript; allow retry with a cleaner recording. |
| R-02 | **Overlapping speakers.** Crosstalk confuses diarization and word attribution; WhisperX documentation states overlap is not handled well. | High | High | Use exclusive diarization for attribution; flag overlap when engine exposes it; avoid claiming per-word certainty; test overlap fixtures. | Assign the dominant speaker, mark overlap/unknown; future source separation. |
| R-03 | **Similar-sounding voices.** Diarization merges or splits speakers with similar timbre. | Medium | High | Speaker-count hints; community-1 pipeline; deterministic labels; surface uncertainty; evaluate on a small consented set. | Merge/split remains; UI shows anonymous labels and a limitation notice; future manual correction. |
| R-04 | **Long recordings.** Multi-hour files stress memory, timeouts, progress tracking, and artifact size. | Medium | High | Default 4 h cap; VAD-batched inference; one job at a time; heartbeat; stage checkpoints; chunking with overlap if needed. | Reject over-cap files with a clear message; process shorter segments; future chunked upload/processing. |
| R-05 | **Memory consumption.** Loading Whisper, alignment, and pyannote models together can exhaust RAM/VRAM. | High | High | Load models per stage and free them; configure batch/compute type; one concurrent job; monitor memory; smaller models on constrained hosts. | Retry with smaller batch/model; fail with `RESOURCE_EXHAUSTED`; run stages in separate processes. |
| R-06 | **CPU/GPU limitations.** Hardware is unknown; CPU-only processing is much slower and may not fit the demo timeline. | High | High | Hardware discovery gate in Part 2; device detection; CPU int8 fallback; documented model matrix; no assumption of CUDA. | CPU + `small`/`base` model; limit demo duration; reduce concurrency. |
| R-07 | **Slow transcription.** Long jobs can exceed demo or user patience even on GPU; CPU can be far slower than real time. | High | Medium | Progress UI; benchmark per hardware; choose model/batch after measurement; avoid reprocessing stable artifacts. | Accept longer waits with status; use a shorter demo recording; smaller model. |
| R-08 | **Model download failures.** First-run downloads can fail due to network, gating, disk, or registry issues. | Medium | High | Preflight download command; local model cache; checksums; offline mode; document HF token/terms; demo preflight. | Restore from a prepared cache; retry; fail with `MODEL_UNAVAILABLE`; no silent fallback that hides the issue. |
| R-09 | **Diarization errors.** Wrong speaker count, swapped labels, fragmented turns, or missed speech. | High | High | Community-1, speaker hints, exclusive diarization for attribution, DER evaluation, explicit degraded status. | Single-speaker degradation notice; future manual correction; never claim perfect labels. |
| R-10 | **Word alignment errors.** Tokens like numbers/currency may be unalignable; model/language gaps; boundaries can be approximate. | High | Medium | Language-specific alignment; fallback ladder; null times for unaligned tokens; quality flags; synthetic marker tests. | Use ASR word times or segment-level timing; UI labels estimated timing. |
| R-11 | **Video synchronization drift.** Audio extraction offsets, edit lists, or browser timeline normalization shift transcript times. | Medium | High | FFprobe-derived offset; apply once; synthetic beep/marker fixtures; test Range seeking; log offsets; tolerance targets. | Segment-level timing; configurable offset correction (future); transcript-only mode. |
| R-12 | **Large uploads.** Multi-GB files can time out, exhaust memory, or hit proxy limits. | Medium | High | Streaming upload; byte cap; disk-space precheck; server/proxy timeout config; no in-memory buffering; progress. | Reject with `FILE_TOO_LARGE`; future resumable/chunked upload; compress before upload guidance. |
| R-13 | **Processing interruptions.** Worker/API crash, power loss, or container restart mid-pipeline. | Medium | High | Durable job rows; atomic claim; heartbeat/lease; stage artifacts; idempotent DB transaction; graceful shutdown. | Reclaim stale job; resume from last valid artifact; restart pipeline if artifacts are invalid. |
| R-14 | **Storage limitations.** Original + WAV + artifacts can exceed disk; purge may fail. | Medium | High | Capacity checks; retention policy; delete audio/artifacts after success if configured; purge worker; monitor free space. | Reject new uploads when below threshold; manual cleanup; external drive/object storage future. |
| R-15 | **Browser codec incompatibility.** MKV/HEVC or unusual audio may be decodable by FFmpeg but not playable in the browser. | Medium | High | Validate browser-playable codecs at upload; accept only known combinations; clear rejection message; consider proxy in Part 5. | Transcript-only view; future H.264/AAC proxy transcode. |
| R-16 | **Model licensing/attribution.** community-1 is CC-BY-4.0; 3.1 is MIT but gated; alignment checkpoints vary; FFmpeg build license varies. | Medium | Medium | Record licenses and attribution; choose model deliberately; verify model cards; include notices in repo/report. | Use MIT 3.1 pipeline if CC-BY-4.0 is unacceptable; replace alignment model. |
| R-17 | **SQLite contention/corruption.** Concurrent writes or unsafe shutdown can lock the DB; file corruption is possible without backups. | Low | High | WAL, busy timeout, short transactions, one writer; backup before migrations; integrity checks. | Restore backup; switch to PostgreSQL if concurrency grows. |
| R-18 | **ASR hallucination/spurious text.** Silence, music, or noise can produce repeated or invented text. | High | Medium | VAD, no-speech/compression thresholds, loop detection, drop-and-log policy, quality warnings. | Empty/partial transcript with warning; manual review; do not present as certain. |
| R-19 | **Privacy/security incident.** Meeting recordings are sensitive; path traversal, malicious media, exposed URLs, or logs could leak content. | Low | Critical | Local processing; no third-party AI API; allowlists; server paths; argv FFmpeg; no content logging; auth before any public deployment; deletion. | Take the service offline; rotate tokens; remove exposed files; document incident. |
| R-20 | **Scope creep and academic timeline.** Adding auth, sharing, editing, cloud infra, or perfect accuracy can consume the schedule. | High | High | Enforce MVP non-goals; roadmap gates; defer enhancements; weekly scope review; record changes. | Cut non-essential features; deliver a smaller but honest vertical slice. |

---

## 3. Deep dives on critical risks

### R-01: Poor recording quality

- **Why it matters:** No ASR or diarization model can recover speech that is unintelligible or overwhelmed by noise. Quality varies widely across Google Meet recordings.
- **Trigger/early warning:** Low RMS, high clipping ratio, long non-speech regions, WER above the agreed sample threshold, or repeated ASR uncertainty.
- **Mitigation detail:** Persist diagnostics before ASR. Provide user guidance (use the original recording, avoid re-encoding, ensure microphones are audible). Do not apply aggressive enhancement by default. Evaluate with both clean and noisy fixtures.
- **Residual risk:** High. The system must communicate that accuracy is best-effort.

### R-02: Overlapping speakers

- **Why it matters:** Diarization cannot reliably assign simultaneous speech, and word attribution must choose a dominant speaker or unknown.
- **Trigger/early warning:** Many words intersect multiple turns; frequent speaker switches within short windows; diarization turns conflict with ASR segment boundaries.
- **Mitigation detail:** Use exclusive diarization for attribution and regular turns for overlap flags. Mark `is_overlap`, choose the dominant overlap, and state the limitation. Do not attempt to split overlapped words in the MVP.
- **Residual risk:** High; overlap attribution remains approximate.

### R-04: Long recordings

- **Why it matters:** A 4-hour file produces a large WAV, many segments, and long model runtimes. A single crash near the end is costly.
- **Trigger/early warning:** Duration near the cap, high memory growth, heartbeat gaps, stage timeouts.
- **Mitigation detail:** Enforce a configurable cap, use batched inference, checkpoint each stage, and keep artifacts. For extreme durations, process windows with overlap and global offsets; test boundary deduplication.
- **Residual risk:** Medium after checkpointing; still slow.

### R-11: Video synchronization drift

- **Why it matters:** A transcript that is consistently offset is perceived as broken even if the text is correct.
- **Trigger/early warning:** Seeks land before/after audible speech; offset differs by browser; transcript end exceeds duration; edit-list files.
- **Mitigation detail:** Compute offset from FFprobe, apply once, test with synthetic markers at 5/30/60 s, and verify in Chrome and one other browser. Record the offset in `audio.json` and the API metadata.
- **Residual risk:** Medium; unusual containers may need a manual correction feature in a future part.

### R-13: Processing interruptions

- **Why it matters:** A worker crash during transcription can waste minutes/hours and leave the user with a stuck job.
- **Trigger/early warning:** Heartbeat older than the lease, process restarts, repeated attempts, `SIGTERM` during a job.
- **Mitigation detail:** Durable queue rows, atomic claim, heartbeat, bounded retries, stage artifacts, and a transaction that commits the transcript only when complete. Handle graceful shutdown by releasing the job/lease.
- **Residual risk:** Low after Part 14, provided artifacts are valid.

### R-16: Model licensing and attribution

- **Why it matters:** The academic submission and repository distribution must comply with model licenses. Current WhisperX uses `pyannote/speaker-diarization-community-1` (CC-BY-4.0); older 3.1 is MIT. FFmpeg build flags can change obligations.
- **Trigger/early warning:** Model changes, new alignment checkpoint, distribution of a bundled binary, or submission without notices.
- **Mitigation detail:** Record every model and license in the ADR and report. Include attribution for CC-BY-4.0. Verify at Part 2 and again before Part 16. Choose 3.1 if the team cannot accept CC-BY-4.0 terms.
- **Residual risk:** Low if documented; legal interpretation is outside the project's expertise.

---

## 4. Risk matrix

```text
Impact
Critical | R-19
High     | R-09 R-13 R-14 R-15      R-01 R-02 R-05 R-06 R-12 R-20
Medium   | R-10 R-16 R-17 R-18      R-03 R-07 R-08 R-11
Low      |
         +--------------------------------------------------------
           Low                      Medium                 High
                                 Probability
```

This is a qualitative planning aid, not a quantitative model.

---

## 5. Monitoring and early warning

| Signal | Why | Response |
|---|---|---|
| Upload rejection rate by code | Detects format/size friction | Improve guidance or proxy support. |
| Job failure rate by stage | Finds the weak link | Tune model/config; add fallback. |
| p95 processing duration by duration bucket | Detects slowdowns | Adjust batch/model; set expectations. |
| OOM/resource-exhausted count | Detects memory pressure | Reduce batch/concurrency; free models. |
| Heartbeat gaps/stale jobs | Detects crashes/hangs | Reclaim and inspect logs. |
| Disk free percentage | Prevents silent failures | Reject uploads; purge; alert. |
| Diarization fallback rate | Measures missing tokens/models | Fix preflight/cache. |
| WER/DER/timestamp error on fixtures | Tracks quality regressions | Block release if unacceptable. |
| Sync E2E failures | Protects core UX | Investigate offset/player logic. |
| Model cache presence | Demo readiness | Preflight before demonstration. |

---

## 6. Residual and accepted risks

- **ASR/diarization are probabilistic.** No configuration guarantees perfect output. This is accepted and must be stated in the UI and academic report.
- **Hardware is unknown.** Performance and model choice are unresolved until Part 2. The architecture supports CPU fallback, but speed is not guaranteed.
- **Privacy depends on deployment.** Local processing reduces third-party exposure, but an unauthenticated public deployment would be unsafe. The MVP must not be exposed publicly without auth.
- **Browser codec support is outside our control.** Rejection or transcript-only mode is an acceptable MVP fallback.
- **CC-BY-4.0 attribution** is an accepted obligation if community-1 is used; the team must confirm this choice.
- **Quality metrics are not yet measured.** Any accuracy claim before Part 15 is unsupported.

---

## 7. Review cadence

- Re-score this register after Part 5 (media/timeline), Part 6 (ASR/hardware), Part 7 (diarization), and Part 15 (full test).
- Record changes and rationale in `CHANGELOG.md` and, when architectural, in `ARCHITECTURE_DECISIONS.md`.
- Do not close a risk based only on code existing; require evidence from an executed test or benchmark.
