# Prompt Iteration Log - SCSE4041 Milestone 2

| Field | Value |
|---|---|
| Document ID | M2-PROMPT-ITER |
| Version | 0.1.0 |
| Last updated | 2026-11-20 |
| Status | Version 1 recorded; versions 2-3 not yet created |

> The final academic submission requires **at least three meaningful prompt versions**. As of Part 1, only one prompt has actually been used. This document records that version honestly and leaves explicit placeholders for future versions. Do not invent iterations, outcomes, or metrics.

---

## 1. What counts as a meaningful iteration

A new version is meaningful when it changes at least one of:

- The task objective or scope.
- A hard constraint (for example: no cloud APIs, must run on CPU, exact output format).
- The required evidence or acceptance criteria.
- The architecture/design direction (after a documented review).
- A verified defect in the previous prompt's instructions.

A version is **not** meaningful if it only fixes typos or reorders wording without changing intent.

---

## 2. Iteration summary

| Version | Date | Prompt file | Intent | Status | Evidence |
|---|---|---|---|---|---|
| V1 | 2026-11-20 | `prompts/PROMPT_01_PROJECT_ANALYSIS.md` | Complete Part 1 analysis and documentation | Executed | Documentation set + self-check report |
| V2 | TBD | TBD | Not yet created | Pending | None |
| V3 | TBD | TBD | Not yet created | Pending | None |

**Requirement status:** 1 of 3 minimum versions recorded. This is intentionally incomplete and must be finished with real iterations before submission.

---

## 3. Version 1 (actual)

| Field | Value |
|---|---|
| Version | V1 |
| Date | 2026-11-20 |
| Prompt | `prompts/PROMPT_01_PROJECT_ANALYSIS.md` |
| Model context | `opencode/deepseek-v4.1-flash-free` (as reported by the environment) |
| Goal | Produce Part 1 architecture and documentation only; no code, no dependency installation |
| Key constraints | Modular monolith; no microservices/Kubernetes; anonymous speakers; local processing; honest verification; no fabricated hardware/tests/team data; Mermaid diagrams; 10 docs + changelog |
| Output | Documentation set created in `docs/`; `CHANGELOG.md`; no application code |
| Verification performed | Workspace inspection; file existence; content consistency review; diagram syntax reviewed manually (not machine-rendered) |
| Verification not performed | No runtime tests, no model evaluation, no browser tests (no implementation exists) |
| Issues found | Official SCSE4041 seven-section titles were not provided; hardware/GPU specs unknown; exact ML versions intentionally unpinned |
| Follow-up needed | Part 2 initialization, version pinning spike, hardware confirmation, HF token/license decision |

**Why this version:** It is the initial prompt issued for the project. It is recorded as V1, not as an "iteration" produced by refinement.

---

## 4. Version 2 (pending)

Do not fill this section until a real prompt is issued and used.

Suggested trigger (not an invented event): after Part 2's compatibility spike, a follow-up might need to add the confirmed hardware constraints, exact pinned versions, and a revised model choice. The actual prompt text, date, and outcome must be recorded at that time.

| Field | Value |
|---|---|
| Version | V2 |
| Date | TBD |
| Prompt file | TBD |
| What changed vs V1 | TBD |
| Why it changed | TBD |
| Output/evidence | TBD |
| Regression/impact | TBD |

---

## 5. Version 3 (pending)

Do not fill this section until a real prompt is issued and used.

Suggested trigger (not an invented event): after Part 15 testing, a prompt might need to incorporate measured WER/DER/timestamp results, revise claims, and update the report. The actual prompt and evidence must be recorded then.

| Field | Value |
|---|---|
| Version | V3 |
| Date | TBD |
| Prompt file | TBD |
| What changed vs V2 | TBD |
| Why it changed | TBD |
| Output/evidence | TBD |
| Regression/impact | TBD |

---

## 6. Iteration review template

Copy this section for each new version:

```text
Version:
Date:
Author (team role, not inferred):
Prompt file:
Previous version:
Change category: scope | constraint | evidence | architecture | defect fix
Exact change summary:
Reason for change:
Evidence that motivated it:
Outputs affected:
Verification performed:
Known limitations:
```

---

## 7. Integrity rules

- Never fabricate a prompt, date, outcome, or test result to satisfy the "three versions" requirement.
- If fewer than three meaningful versions exist by submission, state that honestly and explain why; do not invent filler.
- Keep archived prompt files immutable; add new files for new versions.
- Update the summary table and `CHANGELOG.md` when a version is added.
