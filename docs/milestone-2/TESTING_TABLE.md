# Testing Table - Planned Cases and Evidence

| Field | Value |
|---|---|
| Document ID | M2-TEST-001 |
| Version | 0.1.0 |
| Last updated | 2026-11-20 |
| Status | Planned only - no tests executed |
| Related documents | `PROJECT_REQUIREMENTS.md`, `AI_PIPELINE_DESIGN.md`, `DEVELOPMENT_ROADMAP.md` |

> **Critical honesty note:** No application exists yet. Every row below is **NOT EXECUTED**. The "Actual result" and "Evidence" columns are intentionally empty. Do not mark a test PASS until the application exists and the test has actually run. This table is a plan, not a result.

---

## 1. Scope

The final Milestone 2 submission requires at least ten input tests and three edge cases. This plan defines twelve normal cases and eight edge/adversarial cases. Additional API, unit, and quality tests will be added in Parts 4-15.

Each row records:

- The input fixture and preconditions.
- The expected observable result.
- The actual result and evidence after execution.
- Status: `NOT EXECUTED`, `PASS`, `FAIL`, `BLOCKED`, or `PARTIAL`.

---

## 2. Normal input cases

| ID | Input / fixture | Preconditions | Expected result | Actual result | Status | Evidence |
|---|---|---|---|---|---|---|
| T-01 | MP4, H.264/AAC, 1080p, 5 min, 3 speakers, clean audio | App running; models cached; worker running | Upload accepted; 3 anonymous speakers (subject to engine accuracy); chronological transcript; segment timestamps within tolerance | - | NOT EXECUTED | - |
| T-02 | MOV, H.264/AAC, 2 min, 2 speakers | Same | Upload accepted; video playable; 2 speakers; transcript and seeking work | - | NOT EXECUTED | - |
| T-03 | WebM, VP9/Opus, 3 min, 2 speakers | Same | Upload accepted; video playable; transcript and seeking work | - | NOT EXECUTED | - |
| T-04 | MP4, 30 s, single speaker | Same | One speaker labeled "Speaker 1"; no phantom speakers; short transcript displayed | - | NOT EXECUTED | - |
| T-05 | MP4, 10 min, 4 speakers, includes crosstalk | Same | 4 speakers (best-effort); overlap flagged where detected; transcript remains ordered | - | NOT EXECUTED | - |
| T-06 | MP4, 60 min, 3 speakers | Same | Completes without OOM; status progresses; transcript commit is atomic; player seeks correctly | - | NOT EXECUTED | - |
| T-07 | MP4, exactly at configured duration cap | Test cap configured lower than production for speed | Boundary case accepted; one second over cap rejected with `DURATION_EXCEEDED` | - | NOT EXECUTED | - |
| T-08 | MP4, non-English speech (for example Spanish), 3 min | Alignment model availability verified | Language detected or hinted; transcript produced; alignment quality reported honestly; fallback works if no alignment model | - | NOT EXECUTED | - |
| T-09 | MP4, noisy recording, 5 min, 2 speakers | Same as T-01 | Transcript produced with lower confidence; quality warning shown; no false claim of accuracy | - | NOT EXECUTED | - |
| T-10 | Crafted MP4 with audio stream delayed relative to video | FFprobe metadata recorded | Offset computed; transcript shifts by the correct amount; seeking lands on the audible marker | - | NOT EXECUTED | - |
| T-11 | File at the configured upload-size boundary (use a reduced test cap, not 2 GiB) | Test cap configured | Boundary accepted; cap+1 rejected with `FILE_TOO_LARGE`; no partial file remains | - | NOT EXECUTED | - |
| T-12 | MP4, 1 h, 3 speakers, includes numbers/currency/URLs | Same as T-06 | Unalignable tokens are preserved with `segment_only` timing; no fabricated word times; transcript readable | - | NOT EXECUTED | - |

---

## 3. Edge and adversarial cases

| ID | Input / condition | Preconditions | Expected result | Actual result | Status | Evidence |
|---|---|---|---|---|---|---|
| E-01 | Video-only file with no audio stream | App running | Rejected before meeting creation with `NO_AUDIO_STREAM`; no orphan row/file | - | NOT EXECUTED | - |
| E-02 | Corrupt/truncated MP4 (renamed to `.mp4`) | App running | Rejected with `UNPROCESSABLE_MEDIA`; temp file cleaned; original not retained | - | NOT EXECUTED | - |
| E-03 | Unsupported/browser-unplayable input (for example HEVC/MKV) | App running | Rejected with `UNSUPPORTED_FORMAT` or `NOT_BROWSER_PLAYABLE`; accepted-format guidance shown | - | NOT EXECUTED | - |
| E-04 | Zero-byte file | App running | Rejected with `VALIDATION_ERROR` or `UNPROCESSABLE_MEDIA`; no meeting row | - | NOT EXECUTED | - |
| E-05 | Upload with filename `../../evil.mp4` and misleading MIME type | App running | Stored under a server-generated path; no traversal; validation uses content/probe; display name sanitized | - | NOT EXECUTED | - |
| E-06 | Diarization run without a valid HF token | Models otherwise available | Job degrades to single speaker with `DIARIZATION_UNAVAILABLE`; UI notice; no silent claim of multiple speakers | - | NOT EXECUTED | - |
| E-07 | Worker killed during transcription | A job is running | Lease expires; job is reclaimed/retried; no duplicate or partial transcript committed; failure surfaced if attempts exhausted | - | NOT EXECUTED | - |
| E-08 | Disk full during upload or audio extraction | Low-disk test environment | Upload fails with `STORAGE_FULL`; no meeting row; temp files cleaned; extraction failure is retryable | - | NOT EXECUTED | - |
| E-09 | Click timestamp on a segment boundary and in a silence gap | Completed meeting with gaps | Boundary seeks to the intended segment; silence gap does not falsely highlight a segment; Follow behaves correctly | - | NOT EXECUTED | - |
| E-10 | Video stream Range request: valid, invalid, and `bytes=0-` | Completed meeting | `206` with correct `Content-Range`; invalid range returns `416`; full request returns `200`; seeking works in browser | - | NOT EXECUTED | - |

---

## 4. Quality evaluation plan

These are not pass/fail unit tests. Report actual values, dataset details, hardware, model versions, and parameters. Do not claim results before measurement.

| Metric | Method | Dataset | Target | Result |
|---|---|---|---|---|
| WER | Compare transcript to a manually corrected, consented fixture using a standard WER library | To be defined (small, consented) | No fixed guarantee; report measured value | Pending |
| DER | Compare diarization to RTTM ground truth with no forgiveness collar, including overlap | Same consented sample | No fixed guarantee; report measured value | Pending |
| Speaker-count accuracy | Compare detected count to ground truth for 1-5 speakers | Fixtures T-01..T-05 | Report per fixture | Pending |
| Segment start error | Synthetic spoken/beep markers at known times | Crafted fixtures | Target ±500 ms on clean audio (validate, do not guarantee) | Pending |
| Word boundary error | Forced-alignment markers | Crafted fixtures | Target ±300 ms on clean audio (validate, do not guarantee) | Pending |
| Sync accuracy | Browser E2E click-to-seek and highlight boundaries | T-01/T-05 | No incorrect segment highlight outside tolerance | Pending |
| Runtime | Per-stage wall-clock and peak memory | Actual hardware | Report; no universal target | Pending |

---

## 5. Evidence protocol

When a test is executed, record:

1. Date and executor (team role or name if provided by the team).
2. Application commit/build identifier.
3. Hardware and OS.
4. Model names and pinned versions.
5. Fixture identifier, duration, language, speaker count, and consent/license status.
6. Exact command or UI steps.
7. Observed result, including logs/error codes.
8. Screenshot, video, or log path.
9. Status and any follow-up defect ID.

**Rules**

- Do not fill "Actual result" from expectations.
- Do not reuse another test's screenshot as evidence.
- Do not mark PASS for a test that was skipped or blocked.
- Do not include private meeting content in the repository without consent.
- Large media fixtures should live outside the repository with a documented checksum.

---

## 6. Traceability

| Test group | Requirements covered |
|---|---|
| T-01..T-04 | FR-A, FR-B, FR-C, FR-F, FR-G, FR-H |
| T-05, T-08, T-09 | FR-C, FR-D, FR-E, FR-F |
| T-06, T-07, T-11 | FR-A, NFR-05, NFR-07, NFR-09 |
| T-10 | FR-B-04, FR-E-05, FR-E-07 |
| T-12 | FR-E-03, FR-F-04 |
| E-01..E-05 | FR-A-04, FR-A-05, FR-A-06, NFR-10 |
| E-06 | FR-D-07, NFR-12 |
| E-07, E-08 | NFR-07, NFR-09, R-13, R-14 |
| E-09, E-10 | FR-G-03..FR-G-07, NFR-06 |
