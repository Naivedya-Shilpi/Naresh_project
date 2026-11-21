# PROMPT 01 — PROJECT ANALYSIS & SYSTEM ARCHITECTURE

## 1. YOUR ROLE

Act as a Senior Software Architect, Full-Stack Developer, AI/ML Engineer and Technical Documentation Specialist.

You are responsible for designing a scalable, modular and reliable AI-powered meeting transcription platform inspired by Fireflies.ai.

Think like an experienced software architect. Analyze requirements, evaluate technologies, identify risks and make technically justified decisions.

You must complete ONLY Part 1 of the 16-part development roadmap.

Do not start implementing the application.

---

# 2. PROJECT VISION

We are building a web application that allows users to upload recorded Google Meet videos and receive a complete, speaker-separated, timestamped transcript.

The expected user workflow:

1. User opens the website.
2. User uploads a recorded Google Meet video.
3. Backend validates and stores the video.
4. System extracts audio from the video.
5. Speech recognition converts the audio into text.
6. Speaker diarization identifies different speakers.
7. System assigns consistent anonymous speaker labels:
   - Speaker 1
   - Speaker 2
   - Speaker 3
   - Speaker N
8. System generates timestamps for dialogue and individual words where possible.
9. System combines transcription, speaker identification and timestamps.
10. Frontend displays the video player alongside the transcript.
11. Clicking a transcript timestamp moves the video to the corresponding position.
12. During playback, the currently spoken dialogue is highlighted.

### Expected transcript example

Speaker 1 — 00:00:04

"Good morning everyone. Let's begin today's meeting."

Speaker 2 — 00:00:09

"Good morning! I have prepared the project updates."

Speaker 3 — 00:00:15

"Perfect. Let's start with the development progress."

### Important requirements

- Preserve chronological conversation order.
- Speaker IDs must remain consistent throughout a recording.
- Timestamps must correspond to the original video's timeline.
- The transcript must support interactive video synchronization.
- Do not claim perfect speaker identification or 100% transcription accuracy.
- Anonymous speaker labels are sufficient for the initial version. Actual participant identity recognition is not required.

---

# 3. PROPOSED TECHNOLOGY STACK

Evaluate the following technologies and recommend the most appropriate combination.

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS
- HTML5 Video Player

### Backend
- Python
- FastAPI
- REST API
- Pydantic

### Database
- SQLite
- SQLAlchemy
- Alembic

### AI/ML technologies

Evaluate:

1. OpenAI Whisper
2. Faster-Whisper
3. WhisperX
4. Pyannote.audio

For each technology, explain:

- Purpose.
- Architecture.
- Advantages.
- Disadvantages.
- Hardware requirements.
- CPU/GPU compatibility.
- Installation complexity.
- Licensing.
- API key requirements.
- Suitability for our application.

Determine which combination should be used for the MVP.

Pay particular attention to compatibility between speech recognition, speaker diarization and word-level alignment.

Do not assume that these technologies automatically produce perfectly synchronized results.

### Media processing

Evaluate FFmpeg for:

- Video metadata extraction.
- Audio extraction.
- Audio format conversion.
- Sample rate conversion.
- Audio preprocessing.

### Storage

Recommend how to store:

- Original videos.
- Extracted audio.
- Transcript data.
- Temporary processing files.

Do not store large video files directly inside SQLite.

---

# 4. FUNCTIONAL REQUIREMENTS

Create a detailed functional requirements specification.

Cover these modules:

### Module A — Video Upload
- Upload interface.
- Supported formats.
- File size validation.
- Invalid file handling.
- Upload progress.
- Backend storage.

### Module B — Audio Extraction
- Extract audio using FFmpeg.
- Preserve original media timeline.
- Handle different audio formats.
- Handle extraction failures.

### Module C — Speech Recognition
- Speech-to-text conversion.
- Punctuation.
- Long recordings.
- Multilingual support.
- Poor audio quality.

### Module D — Speaker Diarization
- Identify different voices.
- Assign speaker IDs.
- Maintain speaker consistency.
- Detect speaker changes.
- Handle overlapping conversations.
- Explain limitations.

### Module E — Timestamp Alignment
- Word-level timestamps.
- Sentence/dialogue-level timestamps.
- Start and end times.
- Alignment with original video.

### Module F — Transcript Processing
- Combine transcription and diarization.
- Sort dialogue chronologically.
- Group words into readable segments.
- Associate each segment with a speaker.
- Preserve accurate timestamps.

### Module G — Interactive Video Transcript
- Video playback.
- Clickable timestamps.
- Video seeking.
- Active transcript highlighting.
- Playback synchronization.

### Module H — Meeting Management
- Meeting library.
- View previous recordings.
- Retrieve transcripts.
- Delete meetings.
- Processing status.

For every module, specify its purpose, inputs, outputs and dependencies.

Distinguish MVP features from future enhancements.

---

# 5. SYSTEM ARCHITECTURE

Design a complete modular monolithic architecture.

Explain the responsibilities and communication between:

1. Next.js frontend.
2. FastAPI backend.
3. Database.
4. Video storage.
5. FFmpeg processing.
6. Speech recognition engine.
7. Speaker diarization engine.
8. Timestamp alignment engine.
9. Transcript processing engine.
10. Video synchronization interface.

Create the following Mermaid diagrams:

- High-level system architecture.
- Complete AI processing pipeline.
- Frontend/backend communication flow.
- Video-to-transcript data flow.

Explain every component and its responsibilities.

The architecture should allow individual AI components to be replaced without rewriting the entire application.

Avoid unnecessary microservices and Kubernetes for the initial version.

---

# 6. AI PROCESSING PIPELINE

Design this complete pipeline:

Video Upload
→ File Validation
→ Metadata Extraction
→ Audio Extraction
→ Audio Preprocessing
→ Speech Recognition
→ Speaker Diarization
→ Word-Level Alignment
→ Transcript Processing
→ Chronological Ordering
→ Database Storage
→ Frontend Display

For every stage specify:

- Input.
- Processing logic.
- Output.
- Dependencies.
- Potential failures.
- Error handling.
- Testing requirements.

Explain how timestamps generated from extracted audio will map to the original video's timeline.

Investigate whether WhisperX is suitable for combining transcription, diarization and word alignment, and what additional integration is required.

---

# 7. DATABASE DESIGN

Design the initial database schema.

Consider these entities:

- Users.
- Meetings.
- Videos.
- Speakers.
- Transcript segments.
- Transcript words.
- Processing jobs.

For every entity provide:

- Column name.
- Data type.
- Primary key.
- Foreign key.
- Constraints.
- Relationships.

Create an ER diagram using Mermaid.

Do not implement the database yet.

---

# 8. REST API DESIGN

Propose all major backend endpoints.

Include:

- Upload meeting.
- List meetings.
- Retrieve meeting details.
- Retrieve transcript.
- Retrieve speakers.
- Check processing status.
- Retrieve video information.
- Delete meeting.

For every endpoint provide:

- HTTP method.
- URL.
- Purpose.
- Request structure.
- Response structure.
- Possible error responses.

Do not implement APIs in this part.

---

# 9. FRONTEND ARCHITECTURE

Plan these pages:

1. Dashboard.
2. Upload Meeting.
3. Meetings Library.
4. Meeting Detail.
5. Transcript Viewer.

The Meeting Detail page should contain:

- Video player.
- Transcript panel.
- Speaker labels.
- Timestamps.
- Playback controls.
- Active dialogue highlighting.

Explain:

- Component hierarchy.
- State management.
- API communication.
- Video playback state.
- Transcript synchronization.
- Timestamp click handling.

Provide a component hierarchy diagram.

---

# 10. PROJECT DIRECTORY STRUCTURE

Propose a complete scalable directory structure.

Separate:

- Frontend.
- Backend.
- API routes.
- Database models.
- AI services.
- Audio processing.
- Video processing.
- Transcription.
- Diarization.
- Alignment.
- Storage.
- Tests.
- Documentation.
- Configuration.

Explain the responsibility of each major directory.

The structure should support the entire 16-part roadmap.

---

# 11. DEVELOPMENT ROADMAP

Our project will be implemented in 16 milestones.

| Part | Objective |
|---|---|
| 1 | Project Analysis & Architecture |
| 2 | Project Initialization |
| 3 | Database Design and Implementation |
| 4 | Video Upload System |
| 5 | Video and Audio Processing |
| 6 | Speech-to-Text Integration |
| 7 | Speaker Diarization |
| 8 | Timestamp and Word Alignment |
| 9 | Transcript Processing Engine |
| 10 | Backend API Development |
| 11 | Frontend Dashboard |
| 12 | Video Player Integration |
| 13 | Interactive Transcript |
| 14 | Background Processing |
| 15 | Testing, Security and Optimization |
| 16 | Final Integration and Delivery |

For each part explain:

- Objective.
- Expected implementation.
- Dependencies.
- Deliverables.
- Acceptance criteria.
- Testing requirements.

If you believe the sequence should change, explain why. Do not silently change the roadmap.

---

# 12. TECHNICAL RISKS

Identify and analyze at least the following:

- Poor recording quality.
- Overlapping speakers.
- Similar-sounding voices.
- Long recordings.
- Memory consumption.
- CPU/GPU limitations.
- Slow transcription.
- Model download failures.
- Diarization errors.
- Word alignment errors.
- Video synchronization drift.
- Large uploads.
- Processing interruptions.
- Storage limitations.

For each risk provide:

1. Description.
2. Probability.
3. Impact.
4. Mitigation.
5. Fallback approach.

---

# 13. ARCHITECTURAL DECISION RECORDS

Create documented architectural decisions for:

- Frontend framework.
- Backend framework.
- Database.
- Speech recognition model.
- Diarization model.
- Alignment technology.
- Video storage.
- Background processing.
- API communication.
- Development and deployment environment.

For each decision include:

- Decision.
- Alternatives considered.
- Reasoning.
- Advantages.
- Disadvantages.
- Unresolved concerns.

Clearly distinguish confirmed decisions from recommendations.

Do not invent hardware specifications. If my hardware or GPU availability is unknown, document it as an unresolved decision and recommend a flexible architecture.

---

# 14. SCSE4041 MILESTONE 2 DOCUMENTATION REQUIREMENTS

Our project is also part of the SCSE4041 Prompt Engineering Mini Project.

The final academic submission requires:

1. Milestone 2 PDF with seven prescribed sections.
2. Supporting document PDF.
3. Prototype link.
4. Repository link.
5. Demonstration reel of 90–150 seconds.
6. Prompt sheets.
7. Prompt iteration log with at least three meaningful versions.
8. Testing table with at least ten inputs and three edge cases.
9. Working module status table.
10. Team contribution table.

For this milestone:

- Create a dedicated documentation directory.
- Record the architecture and requirements in Markdown.
- Preserve the exact prompts used during development.
- Maintain dated documentation and changelog entries.
- Do not invent test results.
- Do not invent team information.
- Do not claim that unimplemented modules work.
- Clearly separate planned features from implemented features.

Create a documentation checklist that will help us complete the eventual Milestone 2 submission.

Important: The academic report must reflect the actual project, not fictional progress.

---

# 15. REQUIRED DOCUMENTATION FILES

If a workspace is available, create these files:

docs/
  PROJECT_REQUIREMENTS.md
  SYSTEM_ARCHITECTURE.md
  DATABASE_DESIGN.md
  API_DESIGN.md
  FRONTEND_ARCHITECTURE.md
  AI_PIPELINE_DESIGN.md
  DEVELOPMENT_ROADMAP.md
  TECHNICAL_RISKS.md
  ARCHITECTURE_DECISIONS.md
  MILESTONE_2_CHECKLIST.md

Also create or update:

CHANGELOG.md

If the workspace is unavailable, provide complete document contents in your report and clearly state that files were not created.

Do not claim files were created unless they actually exist.

---

# 16. STRICT EXECUTION RULES

1. Complete only Part 1.
2. Do not implement application code.
3. Do not install dependencies.
4. Do not modify existing application files.
5. Do not execute Part 2.
6. Inspect the existing workspace if available.
7. Do not claim to have inspected files you cannot access.
8. Do not fabricate hardware information.
9. Do not invent test results.
10. Do not skip requirements.
11. Use Mermaid for diagrams.
12. Explain technical decisions with proper reasoning.
13. Do not introduce unnecessary infrastructure.
14. Keep documentation consistent across all files.

---

# 17. FINAL SELF-CHECK REPORT

After completing Part 1, produce a detailed report.

## A. Execution Summary

Explain:
- What was requested.
- What was completed.
- What files were created.
- What architectural decisions were made.

## B. Requirement Verification

Use this table:

| Requirement | Status | Evidence | Explanation |
|---|---|---|---|
| Functional requirements | PASS/PARTIAL/FAIL | | |
| Technology evaluation | PASS/PARTIAL/FAIL | | |
| System architecture | PASS/PARTIAL/FAIL | | |
| AI pipeline | PASS/PARTIAL/FAIL | | |
| Database design | PASS/PARTIAL/FAIL | | |
| API design | PASS/PARTIAL/FAIL | | |
| Frontend architecture | PASS/PARTIAL/FAIL | | |
| Directory structure | PASS/PARTIAL/FAIL | | |
| Development roadmap | PASS/PARTIAL/FAIL | | |
| Technical risks | PASS/PARTIAL/FAIL | | |
| Architecture decisions | PASS/PARTIAL/FAIL | | |
| Milestone 2 checklist | PASS/PARTIAL/FAIL | | |

## C. Failed or Incomplete Requirements

For each incomplete requirement explain:

- What was requested?
- What was not completed?
- Why did it fail?
- What prevented completion?
- What is required to fix it?

If none, explicitly state NONE.

## D. Architectural Concerns

Identify unresolved decisions and risks that may affect subsequent milestones.

## E. File Verification

List every file created and verify its existence and contents.

## F. Final Verdict

Choose exactly one:

PASS — All Part 1 requirements have been completed and verified.

PARTIAL — Some requirements remain incomplete.

FAIL — Major requirements have not been satisfied.

Do not issue PASS simply because files exist.

## G. Next Step

State whether the project is ready for Part 2.

Do not execute Part 2.

---

**FINAL INSTRUCTION**

Your priority is accurate architecture, technical feasibility, documentation quality and honest verification.

Do not rush into coding.

Complete Part 1, generate all available documentation, perform the self-check and wait for further instructions.
