# REST API Design

| Field | Value |
|---|---|
| Document ID | API-001 |
| Version | 0.1.0 |
| Status | Design only - not implemented |
| Last updated | 2026-11-20 |
| Base URL | `/api/v1` |
| Related documents | `DATABASE_DESIGN.md`, `SYSTEM_ARCHITECTURE.md`, `FRONTEND_ARCHITECTURE.md` |

> **Implementation status:** No API exists. These contracts are the target for Parts 4, 10, and 14. FastAPI will generate OpenAPI documentation from Pydantic models; this document defines behavior, not code.

---

## 1. Conventions

| Topic | Convention |
|---|---|
| Format | JSON (`application/json; charset=utf-8`) except uploads and media streaming |
| Naming | `snake_case` for JSON fields |
| IDs | UUIDv4 strings |
| Media time | Integer milliseconds (`start_ms`, `end_ms`, `duration_ms`) |
| Wall-clock time | ISO-8601 UTC with `Z` (for example `2026-11-20T12:00:00Z`) |
| Pagination | `limit` (default 20, max 100) and `offset` (default 0) |
| Sorting | Explicit `sort` parameter; default `-created_at` |
| Errors | One error envelope with a stable `code` |
| Authentication | None in single-user MVP; server resolves a configured local user |
| Versioning | URL path `/api/v1`; breaking changes require a new path |
| CORS | Configured frontend origin only; credentials disabled in MVP |
| Compression | Optional gzip for JSON; never compress video responses |

### 1.1 Error envelope

```json
{
  "error": {
    "code": "UNSUPPORTED_FORMAT",
    "message": "The uploaded file is not a supported video.",
    "details": {
      "detected_container": "matroska",
      "detected_video_codec": "hevc"
    },
    "request_id": "req_01J..."
  }
}
```

Rules:

- `message` is safe for end users; it never contains stack traces, filesystem paths, tokens, or SQL.
- `details` is optional and may contain validated, non-sensitive diagnostics.
- `request_id` is always present and matches server logs.
- Pydantic validation failures are normalized to `VALIDATION_ERROR` with a list of field issues, not FastAPI's default shape.

### 1.2 Error code to HTTP status

| HTTP | Codes (examples) |
|---|---|
| 400 | `VALIDATION_ERROR`, `BAD_REQUEST`, `INVALID_RANGE_HEADER` |
| 404 | `MEETING_NOT_FOUND`, `JOB_NOT_FOUND` |
| 409 | `JOB_ALREADY_RUNNING`, `INVALID_STATE_TRANSITION`, `MEETING_PROCESSING` |
| 410 | `MEETING_DELETED` |
| 413 | `FILE_TOO_LARGE` |
| 415 | `UNSUPPORTED_FORMAT`, `UNSUPPORTED_MEDIA_TYPE` |
| 416 | `RANGE_NOT_SATISFIABLE` |
| 422 | `UNPROCESSABLE_MEDIA`, `NO_AUDIO_STREAM`, `DURATION_EXCEEDED`, `NOT_BROWSER_PLAYABLE` |
| 500 | `INTERNAL_ERROR`, `DB_WRITE_FAILED`, `STORAGE_WRITE_FAILED` |
| 503 | `SERVICE_UNAVAILABLE`, `MODEL_UNAVAILABLE` |
| 507 | `STORAGE_FULL` |

The full processing error/warning catalog is in `AI_PIPELINE_DESIGN.md`, section 9.

### 1.3 Authentication and privacy

The MVP is single-user. The API resolves a configured local owner; clients do not send a user ID. Any deployment beyond localhost requires authentication and object-level authorization before use. Video URLs must never be treated as public sharing links.

---

## 2. Endpoint summary

| Method | URL | Purpose |
|---|---|---|
| POST | `/meetings` | Upload a video and create a meeting/job |
| GET | `/meetings` | List meetings |
| GET | `/meetings/{meeting_id}` | Meeting detail |
| PATCH | `/meetings/{meeting_id}` | Rename meeting |
| DELETE | `/meetings/{meeting_id}` | Soft-delete meeting |
| GET | `/meetings/{meeting_id}/status` | Processing status |
| GET | `/meetings/{meeting_id}/transcript` | Transcript (JSON or export) |
| GET | `/meetings/{meeting_id}/speakers` | Speaker list |
| GET | `/meetings/{meeting_id}/video` | Video metadata |
| GET | `/meetings/{meeting_id}/video/stream` | Video bytes with HTTP Range |
| POST | `/meetings/{meeting_id}/retry` | Retry a failed processing job |
| GET | `/meetings/{meeting_id}/jobs` | Job history |
| GET | `/health` | Liveness/readiness |
| GET | `/capabilities` | Runtime capabilities and limits |

---

## 3. Endpoint specifications

### 3.1 Upload meeting

**`POST /api/v1/meetings`**

**Purpose:** Validate and store one video, create a meeting, and enqueue processing.

**Request:** `multipart/form-data`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `file` | binary | Yes | One video; max bytes and duration from configuration |
| `title` | string | No | 1-200 characters after trim; defaults to sanitized filename stem |
| `language` | string | No | ISO 639-1/BCP-47 hint; omit for auto-detect |
| `min_speakers` | integer | No | 1-10 |
| `max_speakers` | integer | No | 1-10; must be >= `min_speakers` |

Do not send JSON or base64 media. The server streams the body to disk. `Content-Length` is checked when present, but the byte limit is enforced while streaming.

**Response: `201 Created`**

`Location: /api/v1/meetings/{id}`

```json
{
  "id": "8f14e45f-ea2b-4b7a-9d7e-2f4b3c1a9d10",
  "title": "Weekly project sync",
  "status": "queued",
  "language": null,
  "duration_ms": 1830000,
  "speaker_count": null,
  "created_at": "2026-11-20T12:00:00Z",
  "video": {
    "width": 1920,
    "height": 1080,
    "duration_ms": 1830000,
    "size_bytes": 314572800
  },
  "job": {
    "id": "3d0f0f9e-6a6e-4f1a-a4c4-8f4f0a5b7c21",
    "status": "queued",
    "stage": "received",
    "progress_pct": 0
  }
}
```

**Errors**

| Status | Code | Condition |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Missing file, invalid title/hints, malformed multipart |
| 413 | `FILE_TOO_LARGE` | Byte limit exceeded while streaming |
| 415 | `UNSUPPORTED_FORMAT` | Container/codec not accepted |
| 422 | `UNPROCESSABLE_MEDIA` | Corrupt/truncated media, probe failure |
| 422 | `NO_AUDIO_STREAM` | No audio track |
| 422 | `DURATION_EXCEEDED` | Duration over cap |
| 422 | `NOT_BROWSER_PLAYABLE` | Streams cannot be played in supported browsers |
| 507 | `STORAGE_FULL` | Disk full |
| 500 | `STORAGE_WRITE_FAILED` | Filesystem error |

**Behavior**

- No meeting row is created for a rejected upload.
- The original file is stored immutably; the checksum is recorded.
- Duplicate uploads create distinct meetings (deduplication is future work).
- The client should use XHR/fetch with upload progress; upload progress is client-side.

---

### 3.2 List meetings

**`GET /api/v1/meetings`**

**Purpose:** Paginated meeting library, newest first.

**Query parameters**

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `status` | string | all | Comma-separated subset of `queued,processing,completed,failed` |
| `limit` | integer | 20 | 1-100 |
| `offset` | integer | 0 | >= 0 |
| `q` | string | none | Case-insensitive title contains; max 100 chars |
| `sort` | string | `-created_at` | `created_at`, `-created_at`, `title`, `-title` |

Soft-deleted meetings are excluded.

**Response: `200 OK`**

```json
{
  "items": [
    {
      "id": "8f14e45f-ea2b-4b7a-9d7e-2f4b3c1a9d10",
      "title": "Weekly project sync",
      "status": "completed",
      "language": "en",
      "duration_ms": 1830000,
      "speaker_count": 3,
      "created_at": "2026-11-20T12:00:00Z",
      "completed_at": "2026-11-20T12:06:12Z",
      "warnings": []
    }
  ],
  "page": {
    "limit": 20,
    "offset": 0,
    "total": 1,
    "has_more": false
  }
}
```

**Errors:** `400 VALIDATION_ERROR` for invalid status/limit/offset/sort.

---

### 3.3 Meeting detail

**`GET /api/v1/meetings/{meeting_id}`**

**Purpose:** Full meeting metadata for the detail page.

**Response: `200 OK`**

```json
{
  "id": "8f14e45f-ea2b-4b7a-9d7e-2f4b3c1a9d10",
  "title": "Weekly project sync",
  "description": null,
  "status": "completed",
  "language": "en",
  "duration_ms": 1830000,
  "speaker_count": 3,
  "alignment_quality": "word",
  "diarization_status": "completed",
  "warnings": [],
  "error": null,
  "created_at": "2026-11-20T12:00:00Z",
  "completed_at": "2026-11-20T12:06:12Z",
  "video": {
    "id": "c1a2...",
    "original_filename": "meeting.mp4",
    "size_bytes": 314572800,
    "sha256": "...",
    "width": 1920,
    "height": 1080,
    "video_codec": "h264",
    "audio_codec": "aac",
    "duration_ms": 1830000,
    "is_browser_playable": true,
    "stream_url": "/api/v1/meetings/8f14.../video/stream"
  },
  "counts": {
    "speakers": 3,
    "segments": 642,
    "words": 9210
  },
  "active_job": null
}
```

**Errors:** `404 MEETING_NOT_FOUND`, `410 MEETING_DELETED`.

**Notes:** No filesystem paths, model paths, raw speaker labels, or token values are returned.

---

### 3.4 Rename meeting

**`PATCH /api/v1/meetings/{meeting_id}`**

**Purpose:** Update user-editable metadata (title only in MVP).

**Request**

```json
{ "title": "Sprint planning - November" }
```

`Content-Type: application/json`. Title 1-200 characters after trim.

**Response: `200 OK`** - meeting summary (same shape as list item).

**Errors:** `400 VALIDATION_ERROR`, `404 MEETING_NOT_FOUND`, `410 MEETING_DELETED`.

---

### 3.5 Delete meeting

**`DELETE /api/v1/meetings/{meeting_id}`**

**Purpose:** Hide the meeting immediately and request asynchronous purge of files and rows.

**Response: `204 No Content`**

**Errors:** `404 MEETING_NOT_FOUND`; `500 INTERNAL_ERROR`.

**Behavior**

- Idempotent for an already soft-deleted meeting: `204`.
- Sets `status=deleted`, `deleted_at`, cancels any active job, and enqueues a purge job in one transaction.
- Video streaming and detail return `410 Gone` immediately.
- Disk cleanup is asynchronous; the UI must not claim that storage is immediately reclaimed.
- Purge failure leaves a consistent soft-deleted row for retry.

---

### 3.6 Processing status

**`GET /api/v1/meetings/{meeting_id}/status`**

**Purpose:** Poll processing state without loading the transcript.

**Response: `200 OK`**

```json
{
  "meeting_id": "8f14e45f-ea2b-4b7a-9d7e-2f4b3c1a9d10",
  "status": "processing",
  "job": {
    "id": "3d0f0f9e-6a6e-4f1a-a4c4-8f4f0a5b7c21",
    "status": "running",
    "stage": "transcribe",
    "progress_pct": 55,
    "attempts": 1,
    "max_attempts": 3,
    "started_at": "2026-11-20T12:00:05Z",
    "heartbeat_at": "2026-11-20T12:02:10Z"
  },
  "warnings": [],
  "error": null,
  "updated_at": "2026-11-20T12:02:11Z"
}
```

Completed/failed examples include `completed_at` or:

```json
{
  "error": {
    "code": "MEDIA_EXTRACTION_FAILED",
    "message": "Audio could not be extracted from this recording.",
    "retryable": true
  }
}
```

**Errors:** `404 MEETING_NOT_FOUND`, `410 MEETING_DELETED`.

**Polling guidance:** 2 seconds while `queued`/`processing`; stop on `completed`/`failed`. Add jitter. Do not poll faster than 1 Hz in the MVP.

---

### 3.7 Retrieve transcript

**`GET /api/v1/meetings/{meeting_id}/transcript`**

**Purpose:** Return the canonical transcript for the viewer or an export.

**Query parameters**

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `include_words` | boolean | `false` | Include word-level timing |
| `format` | string | `json` | `json`, `srt`, `vtt`, `txt` |

**JSON response: `200 OK`**

```json
{
  "meeting_id": "8f14e45f-ea2b-4b7a-9d7e-2f4b3c1a9d10",
  "language": "en",
  "duration_ms": 1830000,
  "alignment_quality": "word",
  "diarization_status": "completed",
  "warnings": [],
  "speakers": [
    { "id": "s1...", "ordinal": 1, "label": "Speaker 1", "total_speech_ms": 612000 }
  ],
  "segments": [
    {
      "id": "seg1...",
      "sequence_index": 0,
      "start_ms": 4000,
      "end_ms": 8800,
      "speaker_id": "s1...",
      "speaker_label": "Speaker 1",
      "text": "Good morning everyone. Let's begin today's meeting.",
      "is_overlap": false,
      "words": [
        { "text": "Good", "start_ms": 4000, "end_ms": 4210, "timing_source": "aligned", "is_overlap": false }
      ]
    }
  ],
  "counts": { "speakers": 3, "segments": 642, "words": 9210 }
}
```

Rules:

- `words` is present only when `include_words=true`; when omitted, the key may be absent or empty.
- `speaker_id`/`speaker_label` are `null` for unknown speakers; the UI renders "Unknown speaker".
- Word `start_ms`/`end_ms` may be `null` when `timing_source=segment_only`.
- Segments are ordered by `sequence_index` and must already be chronological.
- `alignment_quality` and `diarization_status` must be shown in the UI when degraded.
- An empty transcript returns `200` with empty arrays and a warning; it is not a server error.
- While processing, transcript returns `409 MEETING_PROCESSING` (do not serve partial data).

**Export responses**

- `format=srt`: `text/plain; charset=utf-8`, `Content-Disposition: attachment; filename="meeting.srt"`.
- `format=vtt`: `text/vtt; charset=utf-8`, WebVTT with `<v Speaker 1>` voice spans.
- `format=txt`: `text/plain; charset=utf-8`, `[HH:MM:SS] Speaker 1: text`.
- Exports use segment-level timing; word timing is not required.
- SRT timestamps use `HH:MM:SS,mmm`; VTT uses `HH:MM:SS.mmm`.
- Unsupported format: `400 UNSUPPORTED_EXPORT_FORMAT`.

**Errors:** `404 MEETING_NOT_FOUND`, `409 MEETING_PROCESSING`, `410 MEETING_DELETED`, `400 UNSUPPORTED_EXPORT_FORMAT`.

---

### 3.8 Retrieve speakers

**`GET /api/v1/meetings/{meeting_id}/speakers`**

**Purpose:** Speaker legend and diagnostics.

**Response: `200 OK`**

```json
{
  "meeting_id": "8f14...",
  "speakers": [
    {
      "id": "s1...",
      "ordinal": 1,
      "label": "Speaker 1",
      "total_speech_ms": 612000,
      "word_count": 3012
    }
  ],
  "diarization_status": "completed"
}
```

**Errors:** `404 MEETING_NOT_FOUND`, `410 MEETING_DELETED`. Returns an empty list before completion.

**Notes:** `raw_label` is never exposed. `Speaker N` labels are meeting-scoped.

---

### 3.9 Video metadata

**`GET /api/v1/meetings/{meeting_id}/video`**

**Purpose:** Provide player metadata without loading media bytes.

**Response: `200 OK`**

```json
{
  "meeting_id": "8f14...",
  "content_type": "video/mp4",
  "size_bytes": 314572800,
  "duration_ms": 1830000,
  "width": 1920,
  "height": 1080,
  "video_codec": "h264",
  "audio_codec": "aac",
  "is_browser_playable": true,
  "checksum_sha256": "...",
  "stream_url": "/api/v1/meetings/8f14.../video/stream"
}
```

**Errors:** `404 MEETING_NOT_FOUND`, `410 MEETING_DELETED`, `409 VIDEO_NOT_READY` if the file is missing.

---

### 3.10 Stream video

**`GET /api/v1/meetings/{meeting_id}/video/stream`**

**Purpose:** Serve original video bytes with HTTP Range support for seeking.

**Request headers:** `Range: bytes=start-end` (single range only), optional `If-Range: <etag>`.

**Responses**

- `200 OK` for a full-body request: `Accept-Ranges: bytes`, `Content-Length`, `Content-Type`, `ETag`, `Cache-Control: private, max-age=3600`.
- `206 Partial Content` for a valid range: `Content-Range: bytes start-end/size`, `Content-Length` of the range.
- `416 Range Not Satisfiable` for invalid/unsatisfiable ranges: `Content-Range: bytes */size`.
- `HEAD` is supported (no body).

**Errors:** `404 MEETING_NOT_FOUND`, `410 MEETING_DELETED`, `409 VIDEO_NOT_READY`, `416 RANGE_NOT_SATISFIABLE`.

**Implementation notes**

- Confirm the chosen Starlette/FileResponse version supports Range requests; otherwise implement a small Range responder with tests.
- Only one range is required by the MVP; multi-range requests may return `416` or the full file with `200`, documented consistently.
- Do not transcode on the fly. The original file is streamed as stored.
- The frontend uses this URL directly as the `<video src>`; the browser sends Range requests automatically.
- Authentication/authorization must wrap this endpoint before any multi-user deployment.

---

### 3.11 Retry processing

**`POST /api/v1/meetings/{meeting_id}/retry`**

**Purpose:** Requeue a failed meeting.

**Request:** empty body.

**Response: `202 Accepted`**

```json
{
  "meeting_id": "8f14...",
  "status": "queued",
  "job": {
    "id": "new-job-uuid",
    "status": "queued",
    "stage": "received",
    "progress_pct": 0
  }
}
```

**Errors**

| Status | Code | Condition |
|---|---|---|
| 409 | `JOB_ALREADY_RUNNING` | A queued/running job exists |
| 409 | `INVALID_STATE_TRANSITION` | Meeting is not `failed` |
| 410 | `MEETING_DELETED` | Meeting is soft-deleted |
| 404 | `MEETING_NOT_FOUND` | Unknown meeting |
| 409 | `VIDEO_NOT_READY` | Original file is missing/corrupt |

**Behavior:** clears `error_code`/`error_message`, sets `status=queued`, creates a new job. The old job is retained for history. Completed meetings are not retried in the MVP (reprocessing is a future feature).

---

### 3.12 Job history

**`GET /api/v1/meetings/{meeting_id}/jobs`**

**Purpose:** Debugging and transparency.

**Response: `200 OK`**

```json
{
  "items": [
    {
      "id": "3d0f...",
      "job_type": "process",
      "status": "failed",
      "stage": "transcribe",
      "progress_pct": 40,
      "attempts": 3,
      "max_attempts": 3,
      "error_code": "RESOURCE_EXHAUSTED",
      "error_message": "Processing ran out of memory.",
      "created_at": "2026-11-20T12:00:00Z",
      "started_at": "2026-11-20T12:00:05Z",
      "finished_at": "2026-11-20T12:20:00Z"
    }
  ]
}
```

**Errors:** `404 MEETING_NOT_FOUND`, `410 MEETING_DELETED`.

---

### 3.13 Health

**`GET /api/v1/health`**

**Purpose:** Liveness and readiness.

**Response: `200 OK`**

```json
{
  "status": "ok",
  "database": "ok",
  "storage": "ok",
  "version": "0.1.0",
  "time": "2026-11-20T12:00:00Z"
}
```

Return `503 SERVICE_UNAVAILABLE` if the database or storage root is unavailable. Do not expose secrets, model tokens, or absolute paths.

---

### 3.14 Capabilities

**`GET /api/v1/capabilities`**

**Purpose:** Let the UI explain available features and limits before upload.

**Response: `200 OK`**

```json
{
  "device": "cuda",
  "asr": { "configured": true, "model": "large-v3", "model_cached": true },
  "alignment": { "available": true },
  "diarization": { "configured": true, "requires_hf_token": true, "model_cached": true },
  "limits": {
    "max_upload_bytes": 2147483648,
    "max_duration_ms": 14400000,
    "accepted_containers": ["mp4", "mov", "webm"],
    "max_speakers": 10
  }
}
```

**Errors:** `500 INTERNAL_ERROR`. Never return token values or filesystem paths.

---

## 4. Status and state semantics

### 4.1 Meeting status

| Status | Meaning | Allowed transitions |
|---|---|---|
| `queued` | Job waiting for a worker | `processing`, `failed`, `deleted` |
| `processing` | A job is running | `completed`, `failed`, `queued` (worker lease recovery only), `deleted` |
| `completed` | Transcript committed | `deleted` |
| `failed` | Processing failed | `queued` (retry), `deleted` |
| `deleted` | Soft-deleted | terminal until purge |

### 4.2 Job status

`queued -> running -> succeeded | failed | canceled`. A stale running job is reclaimed as `queued` with an incremented attempt. Terminal jobs are immutable; retry creates a new row.

### 4.3 Progress semantics

`progress_pct` is a heuristic for UI feedback, not a precise measurement. Stages have different costs. The API may report 55% during transcription and jump to 90% after persistence. The UI must not infer remaining time from it.

---

## 5. Upload and streaming implementation notes

- **Upload transport:** `multipart/form-data`; stream to a temp file; enforce limits during the stream. Do not read the entire body into memory.
- **Upload progress:** use XHR (or fetch with a streaming request body where supported). Processing progress comes from `/status`.
- **Timeouts:** configure server and proxy timeouts for large uploads; stream media with chunked responses.
- **Range:** the browser sends `Range` automatically. The endpoint must return `206` and `Content-Range`; otherwise seeking fails or downloads the whole file.
- **Content type:** derive from FFprobe/container, not from the client. Typical: `video/mp4`, `video/webm`, `video/quicktime`.
- **Filename:** `Content-Disposition: inline; filename="..."` uses a sanitized name; never a path.
- **Caching:** private caching for single-user MVP; do not use public CDN caching for private recordings.
- **Concurrency:** at most one active processing job per meeting; stream reads can occur while processing.

---

## 6. Pagination, filtering, and sorting

- Use offset pagination for the MVP. Cursor pagination is future work for very large libraries.
- `total` may be computed with a count query; acceptable at MVP scale.
- `q` is a case-insensitive title substring match. Full-text transcript search is future work.
- Invalid values return `400 VALIDATION_ERROR`, not silent defaults.
- Sort fields are allowlisted; never interpolate user input into SQL ordering.

---

## 7. CORS and frontend integration

- Allow the configured frontend origin(s), methods `GET, POST, PATCH, DELETE, HEAD, OPTIONS`, and headers `Content-Type, Range, If-Range`.
- Expose `Content-Range`, `Accept-Ranges`, `Content-Length`, and `Location` to the browser.
- Credentials are disabled in the single-user MVP.
- If a same-origin reverse proxy is used, CORS can be disabled; the API should still be tested directly.
- Large uploads should go directly to FastAPI in the MVP; a Next.js dev proxy may impose body limits.

---

## 8. Contract testing and OpenAPI

- FastAPI generates `/openapi.json`; keep Pydantic models as the single source of truth.
- Contract tests assert every documented endpoint, status code, and error envelope.
- Generate TypeScript types from OpenAPI in Part 10/12 or maintain a hand-written client with matching tests.
- Treat this document and the OpenAPI schema as synchronized deliverables; a mismatch is a defect.
- Example responses in this document are illustrative and must not be used as test fixtures without validation.

---

## 9. Deferred API surface

| Feature | Reason |
|---|---|
| Authentication/users | Single-user MVP |
| Sharing links | Requires auth/authorization |
| Transcript search | Future enhancement |
| Transcript editing | Future enhancement |
| Speaker rename | Future enhancement |
| Resumable upload | Future enhancement |
| SSE/WebSocket progress | Polling is sufficient |
| Bulk delete | Future enhancement |
| Admin/metrics endpoints | Local deployment; logs suffice |
| Reprocess completed meeting | Future enhancement |
