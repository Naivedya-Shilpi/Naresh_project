# Prompt Log - SCSE4041 Milestone 2

| Field | Value |
|---|---|
| Document ID | M2-PROMPT-LOG |
| Version | 0.1.0 |
| Last updated | 2026-11-20 |
| Status | Active, append-only archive |

> This log records prompts actually used in this project. It does not invent prompts, iterations, results, or team contributions. Archived prompt files are preserved as received; corrections must be recorded as a new version rather than silently rewriting history.

---

## 1. Preservation policy

1. Every development prompt is saved as a separate Markdown file under `docs/milestone-2/prompts/`.
2. The archived file contains the prompt text as received, without editorial cleanup. A short index entry in this log provides date, purpose, and hash.
3. Archived prompt files are not edited. If a prompt needs correction, create a new version (`PROMPT_02...`, `_v2`) and record why.
4. Record the model/tool name only when it is known from the execution environment. Do not guess.
5. A "prompt sheet" for the academic report is a cleaned, human-readable summary derived from the archive; it must reference the archived source.
6. Prompt iterations count as meaningful only when the prompt's intent, constraints, or requested output changed in a way that affected the work. Cosmetic rewording does not count.
7. Never claim a prompt was run if it was not. Never claim an output was evaluated if no evidence exists.

---

## 2. Prompt index

| ID | Date | Part | File | Purpose | SHA-256 |
|---|---|---|---|---|---|
| P-01 | 2026-11-20 | 1 | `prompts/PROMPT_01_PROJECT_ANALYSIS.md` | Project analysis, architecture, requirements, data/API/frontend design, risks, ADRs, roadmap, Milestone 2 documentation | `503b67e646429adacc45d6e6fe1aa182df2e84a4b7612450e9e885737d76ae77` |

The hash is of the archived prompt file as of the date above. Recompute if the file is intentionally versioned.

---

## 3. Execution context

| Field | Value |
|---|---|
| Project | MeetScribe (working title) |
| Execution environment | opencode CLI, macOS (darwin) |
| Model identifier (as reported by the environment) | `opencode/deepseek-v4.1-flash-free` |
| Workspace at start | Empty directory; not a git repository |
| Part completed | Part 1 only |
| Code implemented | None |
| Dependencies installed | None |

This context is recorded for reproducibility. It is not a claim about the quality or validity of outputs.

---

## 4. Prompt-to-output traceability

| Prompt | Primary outputs | Verification |
|---|---|---|
| P-01 | `docs/PROJECT_REQUIREMENTS.md`, `SYSTEM_ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `API_DESIGN.md`, `FRONTEND_ARCHITECTURE.md`, `AI_PIPELINE_DESIGN.md`, `DEVELOPMENT_ROADMAP.md`, `TECHNICAL_RISKS.md`, `ARCHITECTURE_DECISIONS.md`, `MILESTONE_2_CHECKLIST.md`, this log, testing template, `CHANGELOG.md` | File existence and self-check report; no runtime tests because no application exists |

---

## 5. Prompt sheet format (for the academic report)

Each submission-ready prompt sheet should contain:

| Field | Content |
|---|---|
| Prompt ID | P-01, P-02, ... |
| Date and context | When and in which tool/model it was used. |
| Objective | What the prompt was meant to produce. |
| Exact source | Link to the immutable archive file. |
| Constraints | Non-negotiable requirements (scope, privacy, formats, honesty). |
| Expected output | Documents/code/tests requested. |
| Actual output | What was produced, with file links. |
| Verification | What was actually checked and what was not. |
| Limitations | Unresolved items, missing evidence, known unknowns. |

Do not claim an output was verified beyond the recorded evidence.

---

## 6. What still needs to be archived

- Prompt 02 (Project Initialization) and every later part prompt.
- Any follow-up prompts that materially change architecture or scope.
- At least three meaningful iterations for the final Milestone 2 prompt iteration log (see `PROMPT_ITERATION_LOG.md`).

Do not backfill fabricated prompts. Archive only prompts that were actually issued.
