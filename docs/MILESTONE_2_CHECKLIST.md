# Milestone 2 Documentation Checklist - SCSE4041

| Field | Value |
|---|---|
| Document ID | M2-CHK-001 |
| Version | 0.1.0 |
| Last updated | 2026-11-20 |
| Status | Active checklist - Part 1 of 16 |
| Project | MeetScribe (working title) |
| Related documents | All files under `docs/`, `docs/milestone-2/`, `CHANGELOG.md` |

> **Integrity statement:** This checklist separates planned work from implemented work. As of 2026-11-20, no application code, database, API, or AI pipeline exists. No test has been executed. No team members, contributions, links, or results are invented. Items marked complete refer only to documentation that actually exists.

---

## 1. Current status snapshot

| Area | Status |
|---|---|
| Part 1 architecture and documentation | Complete for review |
| Application implementation | Not started |
| Database implementation | Not started |
| AI pipeline implementation | Not started |
| Automated tests | None executed |
| Prototype link | Not available |
| Repository link | Not available (workspace is not a git repository) |
| Demo reel | Not recorded |
| Prompt archive | Prompt 01 archived |
| Prompt iterations | 1 of 3 minimum meaningful versions |
| Testing table | Plan with 22 cases; 0 executed |
| Team contribution data | Not provided |

---

## 2. Required deliverables

| # | Deliverable | Required by brief | Status | Evidence / next action |
|---|---|---|---|---|
| 1 | Milestone 2 PDF with seven prescribed sections | Yes | NOT STARTED | Official section titles not yet confirmed. Build from the Markdown sources once implementation and results exist. |
| 2 | Supporting document PDF | Yes | NOT STARTED | Source documents exist in `docs/`; PDF not produced. |
| 3 | Prototype link | Yes | NOT AVAILABLE | Requires Part 16 deployment and, if public, authentication. |
| 4 | Repository link | Yes | NOT AVAILABLE | `git` repository not initialized. Do this in Part 2 and keep history. |
| 5 | Demonstration reel, 90-150 s | Yes | NOT RECORDED | Storyboard below; record only after the demo flow works. |
| 6 | Prompt sheets | Yes | PARTIAL | Prompt 01 archived verbatim; report-ready sheets not yet produced. |
| 7 | Prompt iteration log, >=3 meaningful versions | Yes | PARTIAL (1/3) | `docs/milestone-2/PROMPT_ITERATION_LOG.md`; add only real versions. |
| 8 | Testing table, >=10 inputs + 3 edge cases | Yes | PLAN ONLY | `docs/milestone-2/TESTING_TABLE.md` has 12 normal + 10 edge cases, none executed. |
| 9 | Working module status table | Yes | AVAILABLE | Section 6; all modules honestly marked not implemented. |
| 10 | Team contribution table | Yes | TEMPLATE | Section 7; no names/percentages inferred. |

---

## 3. Seven prescribed sections

The official SCSE4041 Milestone 2 section titles were **not provided** in the brief available to this workspace. Do not guess and submit. Confirm the exact titles from the course brief, then map the content below.

**Provisional working structure (replace titles before submission):**

| Provisional section | Source material | Status |
|---|---|---|
| 1. Introduction and problem statement | `PROJECT_REQUIREMENTS.md` sections 1-2 | Draft source exists |
| 2. Requirements and scope | `PROJECT_REQUIREMENTS.md` sections 4-7 | Draft source exists |
| 3. Architecture and design | `SYSTEM_ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `API_DESIGN.md`, `FRONTEND_ARCHITECTURE.md`, `AI_PIPELINE_DESIGN.md` | Draft sources exist |
| 4. Implementation | Future code and Part 2-16 evidence | Not started |
| 5. Testing and evaluation | `TESTING_TABLE.md`, future test evidence | Plan only |
| 6. Results, limitations, and discussion | Future measured results; `TECHNICAL_RISKS.md` | Not started |
| 7. Conclusion, future work, and reflection | Future; derived from actual work | Not started |

**Action:** Replace this provisional table with the official seven titles and page/word requirements. Record the source of the official brief in the repository.

---

## 4. Documentation created in Part 1

| File | Purpose | Exists | Reviewed |
|---|---|---|---|
| `docs/PROJECT_REQUIREMENTS.md` | Vision, scope, functional/non-functional requirements | Yes | Yes |
| `docs/SYSTEM_ARCHITECTURE.md` | Components, communication, five Mermaid diagrams, deployment, directory structure | Yes | Yes |
| `docs/DATABASE_DESIGN.md` | Schema, constraints, ER diagram, lifecycle | Yes | Yes |
| `docs/API_DESIGN.md` | Endpoints, requests, responses, errors | Yes | Yes |
| `docs/FRONTEND_ARCHITECTURE.md` | Pages, components, state, sync, hierarchy diagram | Yes | Yes |
| `docs/AI_PIPELINE_DESIGN.md` | 12 stages, timeline mapping, WhisperX assessment | Yes | Yes |
| `docs/DEVELOPMENT_ROADMAP.md` | 16 parts with acceptance/testing criteria | Yes | Yes |
| `docs/TECHNICAL_RISKS.md` | Risk register, deep dives, monitoring | Yes | Yes |
| `docs/ARCHITECTURE_DECISIONS.md` | 15 ADRs, confirmed/recommended/unresolved | Yes | Yes |
| `docs/TECHNOLOGY_EVALUATION.md` | Whisper/faster-whisper/WhisperX/pyannote, FFmpeg, storage evaluation | Yes | Yes |
| `docs/MILESTONE_2_CHECKLIST.md` | This checklist | Yes | Yes |
| `docs/milestone-2/PROMPT_LOG.md` | Prompt archive index and traceability | Yes | Yes |
| `docs/milestone-2/PROMPT_ITERATION_LOG.md` | Version 1 + pending V2/V3 | Yes | Yes |
| `docs/milestone-2/TESTING_TABLE.md` | Planned test matrix and quality plan | Yes | Yes |
| `docs/milestone-2/prompts/PROMPT_01_PROJECT_ANALYSIS.md` | Exact Prompt 01 archive | Yes | Yes |
| `CHANGELOG.md` | Dated documentation changelog | Yes | Yes |

**Not yet created:** README, `.env.example`, repository license, application source, migrations, tests, deployment guide, screenshots, demo video, PDFs.

---

## 5. Part 1 completion checklist

### Requirements and design

- [x] Project vision and user workflow documented.
- [x] MVP vs future scope separated.
- [x] Modules A-H specified with purpose, inputs, outputs, dependencies.
- [x] Frontend/backend/media/AI/storage technology evaluation documented.
- [x] AI technology comparison (Whisper, faster-whisper, WhisperX, pyannote) documented.
- [x] Licensing and API-key requirements documented with verification cautions.
- [x] FFmpeg and storage strategy documented.
- [x] Modular monolith architecture with component responsibilities.
- [x] Four required Mermaid architecture diagrams.
- [x] 12-stage AI pipeline with failures, errors, and testing.
- [x] Audio-to-video timeline mapping formula and caveats.
- [x] WhisperX suitability and integration requirements.
- [x] Database schema, constraints, relationships, ER diagram.
- [x] REST API endpoints with request/response/errors.
- [x] Frontend pages, component hierarchy, state, sync, click handling.
- [x] Directory structure proposal.
- [x] 16-part roadmap with acceptance and testing.
- [x] Technical risks with probability/impact/mitigation/fallback.
- [x] ADRs with confirmed/recommended/unresolved statuses.
- [x] No hardware assumptions or fabricated specs.

### Academic evidence

- [x] Dedicated documentation directory.
- [x] Architecture and requirements in Markdown.
- [x] Exact Prompt 01 archived.
- [x] Prompt log with date, hash, and traceability.
- [x] Prompt iteration log started honestly (1 of 3).
- [x] Testing table plan with >=10 inputs and >=3 edge cases.
- [x] Working module status table.
- [x] Team contribution template.
- [x] Dated changelog.
- [x] PDF-ready content sources.
- [ ] Official seven section titles confirmed.
- [ ] Supporting document PDF produced.
- [ ] Prompt sheets formatted for submission.
- [ ] At least three real prompt iterations recorded.
- [ ] Actual test results recorded.
- [ ] Team contribution data completed.
- [ ] Repository link available.
- [ ] Prototype link available.
- [ ] Demo reel recorded.

---

## 6. Working module status table

**As of 2026-11-20.** "Design" means documentation exists. "Implemented" and "Tested" are strict: no code and no executed tests exist.

| Module | Design | Implemented | Tested | Evidence |
|---|---|---|---|---|
| A. Video upload | Complete | No | No | `PROJECT_REQUIREMENTS.md`, `API_DESIGN.md` |
| B. Audio extraction | Complete | No | No | `AI_PIPELINE_DESIGN.md` stages 4-5 |
| C. Speech recognition | Complete | No | No | `AI_PIPELINE_DESIGN.md` stage 6 |
| D. Speaker diarization | Complete | No | No | `AI_PIPELINE_DESIGN.md` stage 7 |
| E. Timestamp alignment | Complete | No | No | `AI_PIPELINE_DESIGN.md` stages 8-9 |
| F. Transcript processing | Complete | No | No | `AI_PIPELINE_DESIGN.md` stages 9-10 |
| G. Interactive transcript | Complete | No | No | `FRONTEND_ARCHITECTURE.md` |
| H. Meeting management | Complete | No | No | `DATABASE_DESIGN.md`, `API_DESIGN.md` |
| Documentation/ADR | Complete | N/A | N/A | `docs/` |

Do not change "Implemented" to "Yes" until code is merged; do not change "Tested" to "Yes" until evidence is recorded.

---

## 7. Team contribution table (template)

No team names, roles, or percentages were provided in Part 1. Do not infer them. Complete this table manually and keep evidence (commit history, meeting notes, task board).

| Team member | Role | Contribution | Evidence (commits/tasks/docs) | Approx. % |
|---|---|---|---|---|
| `[Team member 1]` | `[Role]` | `[Actual contribution]` | `[Link/screenshot/commit]` | `[TBD]` |
| `[Team member 2]` | `[Role]` | `[Actual contribution]` | `[Link/screenshot/commit]` | `[TBD]` |
| `[Team member 3]` | `[Role]` | `[Actual contribution]` | `[Link/screenshot/commit]` | `[TBD]` |
| `[Team member 4]` | `[Role]` | `[Actual contribution]` | `[Link/screenshot/commit]` | `[TBD]` |

**Rules:** contribution claims must be backed by evidence; percentage columns must sum to 100 only when the team explicitly agrees; remove unused rows.

---

## 8. Prompt preservation and iteration

Source files:

- Archive: `docs/milestone-2/prompts/PROMPT_01_PROJECT_ANALYSIS.md`
- Index: `docs/milestone-2/PROMPT_LOG.md`
- Iterations: `docs/milestone-2/PROMPT_ITERATION_LOG.md`

Checklist:

- [x] Prompt 01 archived.
- [x] Date, purpose, model context, and SHA-256 recorded.
- [x] Archive declared immutable.
- [ ] Prompt 02 archived after Part 2 starts.
- [ ] Every later part prompt archived.
- [ ] Three meaningful prompt versions documented with real changes.
- [ ] Prompt sheets formatted for the academic report.
- [ ] No invented prompts or outcomes.

---

## 9. Testing evidence

- [x] Planned test matrix with 12 normal inputs.
- [x] Planned edge/adversarial matrix with 10 cases.
- [x] Quality metrics plan (WER, DER, timestamp error, sync).
- [x] Evidence protocol defined.
- [ ] Upload tests executed.
- [ ] Media/timeline tests executed.
- [ ] ASR tests executed.
- [ ] Diarization tests executed.
- [ ] Alignment tests executed.
- [ ] Transcript/ordering tests executed.
- [ ] API contract tests executed.
- [ ] Browser E2E tests executed.
- [ ] Quality metrics measured on consented fixtures.
- [ ] Test evidence stored and linked.
- [ ] Actual results copied into the submission table.

Do not copy "expected" text into "actual" columns. Do not report vendor benchmarks as project measurements.

---

## 10. Demo reel storyboard (90-150 seconds)

Record only after the flow is actually working. If a feature fails during recording, show the real failure/limitation or omit the claim.

| Time | Visual | Narration focus |
|---|---|---|
| 0-10 s | Title, project name, one-line problem | Uploaded meetings are hard to navigate; we build a local, timestamped transcript. |
| 10-25 s | Upload page, select a real fixture, show progress | Supported formats, validation, local privacy. |
| 25-40 s | Status panel moving through stages | Long-running work is asynchronous; show real stage/progress (no fake speed claims). |
| 40-65 s | Meeting detail: player + transcript | Speaker labels, timestamps, click a timestamp, video seeks. |
| 65-85 s | Playback with active highlight and Follow | Highlight stays in sync; show a silence gap and speaker change if available. |
| 85-105 s | Speaker legend, degraded/quality notice if applicable | Anonymous labels; explain diarization limits honestly. |
| 105-120 s | Library, delete/retry, or job status | Meeting management and recovery. |
| 120-140 s | Architecture/pipeline slide; limitations | Local WhisperX + pyannote, CPU/GPU variability, no accuracy guarantee. |
| 140-150 s | Repository/prototype link, closing | Where to find the project and documentation. |

Target 120-150 s unless the official limit requires tightening. Keep within 90-150 s.

---

## 11. Supporting document PDF plan

Recommended contents, derived from actual sources:

1. Requirements summary (`PROJECT_REQUIREMENTS.md`).
2. Architecture diagrams and component responsibilities (`SYSTEM_ARCHITECTURE.md`).
3. AI pipeline and timeline mapping (`AI_PIPELINE_DESIGN.md`).
4. Database schema and ER diagram (`DATABASE_DESIGN.md`).
5. API contract summary (`API_DESIGN.md`).
6. Frontend architecture and sync design (`FRONTEND_ARCHITECTURE.md`).
7. Risks and ADRs (`TECHNICAL_RISKS.md`, `ARCHITECTURE_DECISIONS.md`).
8. Test plan and actual results (`TESTING_TABLE.md`; only real results).
9. Prompt log/iteration summary.
10. Limitations, licensing/attribution, and future work.

Export to PDF only after the content reflects the implemented prototype.

---

## 12. Repository and prototype readiness

- [ ] Initialize git in Part 2.
- [ ] Add `.gitignore` for `node_modules`, virtualenv, `data/`, `storage/`, model cache, `.env`.
- [ ] Add `.env.example` without secrets.
- [ ] Add README with setup and hardware requirements.
- [ ] Add license and third-party notices (CC-BY-4.0 attribution if community-1 is used).
- [ ] Add screenshots/GIFs from the real app.
- [ ] Add a fresh-clone setup test.
- [ ] Add a demo preflight script (models cached, DB migrated, storage writable).
- [ ] Add a prototype link (auth required if public).
- [ ] Verify no secrets/large media in git history.

---

## 13. Blockers and open items

| ID | Blocker | Impact | Owner | Needed by |
|---|---|---|---|---|
| B-01 | Official seven-section titles unknown | Cannot finalize PDF structure | Team | Before M2 PDF |
| B-02 | Hardware/GPU specs unknown | Model choice, speed, demo feasibility | Team | Part 2 |
| B-03 | Exact ML dependency versions unpinned | Reproducibility/install failures | Team | Part 2 |
| B-04 | HF token/model terms not confirmed | Diarization cannot run | Team | Part 7 |
| B-05 | community-1 license vs 3.1 choice | Attribution/compliance | Team | Part 7 |
| B-06 | Test fixtures with consent not prepared | Cannot measure quality | Team | Part 15 |
| B-07 | No git repository/prototype link | Submission requirement unmet | Team | Part 2/16 |
| B-08 | Team contribution data absent | Submission table incomplete | Team | Before M2 PDF |
| B-09 | Demo reel not recorded | Submission requirement unmet | Team | Part 16 |

---

## 14. Pre-submission verification

Before submitting Milestone 2:

- [ ] The PDF uses the official seven section titles.
- [ ] Every claim matches implemented behavior and executed evidence.
- [ ] The testing table has >=10 actual inputs and >=3 actual edge cases with results.
- [ ] Failed tests are reported as failures, not hidden.
- [ ] The prompt log has >=3 meaningful versions, or the shortfall is disclosed.
- [ ] All prompts are archived and hashed.
- [ ] The module status table matches the repository state.
- [ ] The team contribution table is complete and evidence-backed.
- [ ] Prototype and repository links work for a reviewer.
- [ ] The demo reel is 90-150 seconds and shows the real app.
- [ ] Known limitations (diarization, accuracy, codecs, hardware) are stated.
- [ ] Model licenses/attribution are included.
- [ ] No secrets, private recordings, or large media are in the repository.
- [ ] `CHANGELOG.md` reflects the final state.
- [ ] A teammate who did not write the document can reproduce the setup.

---

## 15. Documentation consistency rules

1. Use one set of canonical paths: `data/meetscribe.db`, `storage/originals`, `storage/audio`, `storage/artifacts`, `storage/tmp`.
2. Use integer milliseconds for media time and ISO-8601 UTC for wall-clock time.
3. Meeting statuses: `queued`, `processing`, `completed`, `failed`, `deleted`.
4. Speaker labels: `Speaker 1..N`; raw engine labels are internal.
5. Never describe a planned feature as implemented.
6. Never present target tolerances or vendor claims as measured results.
7. Update all affected documents when a decision changes; add a changelog entry.
8. Keep the prompt archive immutable.
