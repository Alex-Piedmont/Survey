# PRD: Classroom Survey Platform

**Version:** 1.0
**Date:** 2026-02-23
**Author:** Product Management
**Status:** Draft
**Project:** Classroom Survey Platform

---

## 1. Introduction / Overview

University courses that rely on live presentations -- such as MGMT 481 -- require structured feedback from three distinct perspectives: audience members, team peers, and the instructor. Today, this feedback is collected through Qualtrics surveys exported to Excel, where Teaching Assistants manually validate attendance, check submission timestamps, cross-reference peer completions, consolidate feedback across teams, and calculate late penalties. This process is error-prone, time-consuming, and disconnects the instructor from real-time insight during class sessions.

The Classroom Survey Platform replaces this manual workflow with a purpose-built web application. Instructors create sessions tied to presentation types, generate QR codes for in-class distribution, and view a live dashboard as students submit feedback. The system automatically enforces submission deadlines, calculates late penalties per syllabus policy, consolidates feedback by team and individual, and flags incomplete or late submissions. Students scan a QR code, authenticate via Google OAuth (with an email-only fallback), and complete structured feedback forms on their devices.

This is a multi-course platform. While the initial deployment targets MGMT 481's three presentation types (Strategic Headlines, Learning Team Debates, Class Strategy Project), any instructor at the university can onboard their course, define custom presentation types, and configure survey templates to match their rubrics.

---

## 2. Goals

- **Eliminate manual TA grading overhead:** Reduce the TA's per-session feedback processing time from hours to under 5 minutes by automating validation, consolidation, and penalty calculation.
- **Enable real-time instructor debrief:** Provide a live dashboard and summary that update within 2 seconds of each student submission, allowing the instructor to debrief the class at any time without waiting for the session to close.
- **Ensure submission accountability:** Automatically track who submitted, when, for which teams, and whether peer feedback obligations were met -- with zero manual cross-referencing.
- **Support multi-course adoption:** Allow any instructor to create a course, define sections, configure presentation types, and run feedback sessions without developer intervention.
- **Allow 7-day revision window:** Students may update their feedback for up to 7 days after the session, with all revisions tracked and late submissions flagged.

### What Success Looks Like

An instructor creates a session for today's Learning Team Debate, generates a QR code, and projects it in class. Students scan the code on their phones, authenticate with Google, and see the feedback form for the presenting team. As students submit, the instructor watches aggregated scores and comment themes populate in real time on their laptop. Once submissions plateau, the instructor closes the session and walks through the summary with the class. That evening, the TA opens the admin view, sees that two students submitted late and one audience member only reviewed one of two teams (flagged automatically), and exports a grade-ready spreadsheet -- all without touching Excel.

---

## 3. User Stories

### US-1: Instructor Creates a Course and Section

**As an** instructor, **I want to** create a course with one or more sections and enroll students by email, **so that** the platform knows who belongs to each section.

**Acceptance Criteria:**
- [ ] Instructor can create a course with a name and term (e.g., "MGMT 481 -- Spring 2026")
- [ ] Instructor can create sections under a course (e.g., "Section A", "Section B")
- [ ] Instructor can bulk-import student emails (CSV upload or paste) into a section
- [ ] Instructor can assign TAs to a section
- [ ] Students appear in the roster with their email as the primary identifier
- [ ] Duplicate emails within a section are rejected with a clear error message

### US-2: Instructor Defines Presentation Types and Survey Templates

**As an** instructor, **I want to** configure presentation types with associated survey templates, **so that** each session uses the correct feedback form.

**Acceptance Criteria:**
- [ ] Instructor can create presentation types (e.g., "Strategic Headlines", "Learning Team Debates", "Class Strategy Project")
- [ ] Each presentation type has a default survey template with audience, peer, and instructor question sets
- [ ] Templates include both Likert-scale (structured) and free-text (qualitative) question types
- [ ] Instructor can toggle individual questions on/off and edit question labels
- [ ] Templates are versioned; changes to a template do not affect already-completed sessions

### US-3: Instructor Creates a Session with QR Codes

**As an** instructor, **I want to** create sessions for a class meeting and generate a unique QR code for each, **so that** students can access the correct feedback form by scanning.

**Acceptance Criteria:**
- [ ] Instructor selects a section, presentation type, date, and assigns the presenting team(s)
- [ ] A single session covers all presenting teams for that presentation type — one QR code shows feedback headers for all assigned teams
- [ ] System generates a unique QR code per session that encodes a URL with the session ID
- [ ] QR codes are displayable full-screen for projection and downloadable as PNG
- [ ] Each session has a configurable deadline (defaults to 11:59 PM day-of with a 30-minute grace period)
- [ ] Instructor can configure the maximum number of sessions allowed per section per class meeting (no hard-coded limit)

### US-4: Student Submits Audience Feedback

**As a** student in the audience, **I want to** scan a QR code and submit feedback for the presenting team, **so that** my participation is recorded and the team receives my evaluation.

**Acceptance Criteria:**
- [ ] Scanning the QR code opens a mobile-friendly feedback form
- [ ] Student authenticates via Google OAuth or enters their university email
- [ ] System validates the student is enrolled in the section
- [ ] Form displays the correct survey template for the session's presentation type
- [ ] Student must complete feedback for ALL presenting teams in the session to receive full participation credit
- [ ] Partial completion (e.g., feedback for 1 of 2 teams) is recorded and flagged
- [ ] Submission timestamp is recorded server-side
- [ ] Student sees a confirmation screen after submission

### US-5: Presenter Submits Peer Feedback

**As a** presenter, **I want to** submit peer feedback for each member of my team, **so that** my participation is recorded and my teammates receive individualized evaluations.

**Acceptance Criteria:**
- [ ] After scanning the QR code, presenters see both audience feedback (for other presenting teams) and a peer feedback section (for their own team)
- [ ] Peer feedback form lists each team member individually (excluding the respondent — no self-evaluation)
- [ ] Presenter must complete peer feedback for every team member to receive full participation credit
- [ ] Incomplete peer feedback is flagged

### US-6: Instructor Views Live Dashboard During Session

**As an** instructor, **I want to** see a real-time dashboard of submissions as students complete feedback, **so that** I can gauge completion and begin the debrief promptly.

**Acceptance Criteria:**
- [ ] Dashboard shows submission count vs. enrolled student count (e.g., "23/35 submitted")
- [ ] Dashboard updates within 2 seconds of each new submission (via WebSocket or polling fallback)
- [ ] Aggregated Likert scores update in real time (mean, distribution)
- [ ] Instructor can see which students have NOT yet submitted (opt-in view)
- [ ] Dashboard is accessible on the instructor's laptop alongside the projected QR code

### US-7: Instructor Reviews Live Summary

**As an** instructor, **I want to** view a live summary of all feedback at any time during or after a session, **so that** I can debrief the class in real time and later assign grades.

**Acceptance Criteria:**
- [ ] Summary view is accessible at any time, even while the session is still accepting submissions
- [ ] Summary updates in real time as new submissions arrive
- [ ] Summary view shows per-team aggregated scores with distributions
- [ ] Summary includes a qualitative section with all free-text comments (anonymized from the presenting team's view)
- [ ] Summary highlights incomplete submissions (partial audience feedback, missing peer feedback)
- [ ] Summary is exportable as CSV and PDF
- [ ] Instructor can add their own feedback/scores through the instructor feedback interface
- [ ] Instructor can assign a presentation quality grade per presenting team (separate from aggregated audience/peer feedback scores)
- [ ] Sessions auto-close at the deadline; no manual close action is needed

### US-8: Student Updates Feedback Within 7-Day Window

**As a** student, **I want to** revise my feedback for up to 7 days after the session, **so that** I can refine my evaluation after reflection.

**Acceptance Criteria:**
- [ ] Student can access their prior submission via a "My Submissions" page
- [ ] Edits are allowed for 7 calendar days after the session date
- [ ] All revisions are timestamped and stored (audit trail)
- [ ] If the original submission was on time but an edit occurs after the deadline, the submission retains its on-time status
- [ ] After 7 days, the form becomes read-only

### US-9: Late Submissions Are Flagged and Penalized

**As a** TA, **I want** late submissions to be automatically flagged with the correct penalty percentage, **so that** I do not have to manually calculate deductions.

**Acceptance Criteria:**
- [ ] Submissions after the deadline + 30-minute grace period are marked "late"
- [ ] Penalty is auto-calculated per the syllabus schedule:
  - 0-24 hours late: 5% deduction
  - 1-2 days late: 10% deduction
  - 2-3 days late: 30% deduction
  - 3-7 days late: 50% deduction
- [ ] Submissions after 7 days are rejected entirely
- [ ] Instructor and TA receive an email notification for each late submission
- [ ] Late status and penalty percentage are visible in the admin dashboard and exports

### US-10: Instructor Exports Grade-Ready Data

**As an** instructor, **I want to** export a consolidated spreadsheet of all feedback, participation status, and penalty calculations, **so that** I can finalize grades efficiently.

**Acceptance Criteria:**
- [ ] Export includes one row per student per session
- [ ] Columns include: student email, submission status (on-time / late / missing), penalty %, audience feedback completion (all teams / partial / none), peer feedback completion, aggregated scores received (as a presenter), and all free-text comments received
- [ ] Export is filterable by section, presentation type, and date range
- [ ] Available as CSV and XLSX

---

## 4. Functional Requirements

### Authentication and Authorization

- **FR-1:** The system shall support Google OAuth 2.0 as the primary authentication method for all users (students, instructors, TAs).
- **FR-2:** The system shall provide an email-only fallback for students whose institutions block third-party OAuth. In this mode, the student enters their email and receives a 6-digit OTP valid for 10 minutes.
- **FR-2a:** As a secondary fallback, the instructor shall be able to manually verify a student's identity from the dashboard (e.g., when OTP delivery is delayed). The instructor selects the student from the enrolled roster, and the system grants that student a session token without requiring OTP or OAuth.
- **FR-3:** The system shall enforce role-based access control with three roles: `instructor`, `ta`, and `student`, scoped per course/section via the `enrollments` table (not a global user attribute). A user may hold different roles in different courses (e.g., instructor in one course, student in another). Instructors have full course management access. TAs have read access to feedback and exports for their assigned sections. Students can only submit and view their own feedback.
- **FR-4:** The first user to create a course is assigned the `instructor` role for that course. Instructors can promote enrolled users to `ta`.

### Course and Section Management

- **FR-5:** A course shall have: `name` (string, max 200 chars), `term` (string, e.g., "Spring 2026"), `created_by` (instructor FK), and `created_at` (timestamp).
- **FR-6:** A section shall belong to exactly one course and have: `name` (string, max 100 chars), `course_id` (FK), and a roster of enrolled student emails.
- **FR-7:** Students shall be enrolled via CSV upload (one email per line) or by pasting a newline-delimited list of emails. The system validates email format and deduplicates.

### Presentation Types and Teams

- **FR-8:** An instructor shall define presentation types per course. Each presentation type has a `name` and an associated survey template.
- **FR-9:** An instructor shall create teams within a section. A team has a `name` and a list of member emails (from the section roster). A student may belong to different teams for different presentation types.

### Survey Templates

- **FR-10:** A survey template shall contain an ordered list of questions, each with:

| Field | Type | Required | Notes |
|---|---|---|---|
| `question_text` | string (max 500 chars) | Yes | The question as displayed to the respondent |
| `question_type` | enum: `likert_5`, `likert_7`, `free_text`, `multiple_choice` | Yes | Determines input widget |
| `category` | enum: `audience`, `peer`, `instructor` | Yes | Determines who sees this question |
| `options` | JSON array of strings | Only for `multiple_choice` | Choice labels |
| `is_required` | boolean | Yes | Whether the question must be answered |
| `sort_order` | integer | Yes | Display order within the template |
| `is_active` | boolean | Yes | Toggled off = hidden from form |

- **FR-11:** The system shall ship with generic default templates for three presentation types (Strategic Headlines, Learning Team Debates, Class Strategy Project) with common feedback questions (content clarity, delivery, teamwork, etc.). These are starting points; instructors are expected to customize them for their rubrics. Instructors using other courses can clone and modify these or create templates from scratch. Qualtrics-based templates can be added later when exports are available.
- **FR-12:** Templates are versioned. When a session is created, it snapshots the current template version. Subsequent template edits do not affect active or completed sessions.

### Sessions and QR Codes

- **FR-13:** A session shall have:

| Field | Type | Required | Notes |
|---|---|---|---|
| `section_id` | FK | Yes | Which section this session belongs to |
| `presentation_type_id` | FK | Yes | Determines which template to use |
| `presenting_team_ids` | array of FK | Yes | One or more teams presenting |
| `session_date` | date | Yes | The class meeting date |
| `deadline` | datetime | Yes | Default: session_date 23:59 + 30 min grace |
| `status` | enum: `open`, `closed` | Yes | Auto-set to `closed` at deadline; no manual close |
| `qr_code_url` | string | Auto-generated | Unique URL encoded in the QR code |
| `template_snapshot_id` | FK | Auto-generated | Frozen copy of the template at creation time |

- **FR-14:** The QR code URL shall follow the pattern: `{frontend_base_url}/s/{session_uuid}`. The UUID shall be a v4 UUID, unguessable.
- **FR-15:** QR codes shall be generated server-side as PNG (minimum 400x400 px) using the `qrcode` Python library. The API shall return the image as a base64-encoded string and a direct image URL.

### Feedback Submission

- **FR-16:** When a student accesses a session URL, the system shall determine their role:
  - If the student is on a presenting team: show both the peer feedback form (for their team) and the audience feedback form (for other presenting teams).
  - If the student is in the audience: show only the audience feedback form for all presenting teams.
- **FR-16a:** The feedback form shall be presented as a multi-page flow, with one page per target (one page per presenting team for audience feedback, one page per team member for peer feedback). Each page is saved to the server individually when the student advances to the next page. This ensures partial progress is preserved if the student loses connectivity or closes the browser.
- **FR-17:** Each feedback submission shall record: `student_email`, `session_id`, `target_team_id` (or `target_student_email` for peer feedback), `responses` (JSON), `submitted_at` (server timestamp), and `is_late` (boolean).
- **FR-18:** A student may submit feedback multiple times for the same target within the 7-day window. Each submission creates a new version; the latest version is used for grading. All versions are retained for audit.
- **FR-19:** After the 7-day window (`session_date + 7 days`), the submission endpoint shall return HTTP 403 with a message indicating the window has closed.

### Participation Tracking

- **FR-20:** The system shall compute a participation status per student per session as a proportional percentage based on completions:

| Scenario | Participation Credit |
|---|---|
| Audience member submitted feedback for ALL presenting teams on time | 100% |
| Audience member submitted feedback for K of N presenting teams on time | K/N × 100% (e.g., 2 of 3 = 67%) |
| Audience member submitted no feedback | 0% |
| Presenter submitted peer feedback for ALL team members on time | 100% |
| Presenter submitted peer feedback for K of N team members on time | K/N × 100% |
| Presenter submitted no peer feedback | 0% |

- **FR-21:** Participation credit is computed independently from the late penalty. A late submission that covers all teams still receives "complete" participation status, but the associated grade is reduced by the late penalty percentage.

### Late Penalty Calculation

- **FR-22:** The system shall auto-calculate penalties per target (per presenting team for audience feedback, per team member for peer feedback) based on the elapsed time between the deadline (including 30-minute grace period) and the initial submission timestamp for that target:

| Elapsed Time | Penalty |
|---|---|
| 0-24 hours | 5% |
| 24-48 hours | 10% |
| 48-72 hours | 30% |
| 72 hours - 7 days | 50% |
| > 7 days | Rejected (not accepted) |

- **FR-23:** The penalty applies to the individual submission's score contribution (per target), not the overall course grade. Penalty overrides are handled outside this platform.

### Live Dashboard

- **FR-24:** The instructor dashboard shall use WebSocket connections (via Socket.IO on Railway) for real-time updates. A polling fallback (5-second interval) shall activate if WebSocket connection fails. V1 assumes a single FastAPI worker; multi-worker scaling with Redis pub/sub adapter is a future consideration.
- **FR-25:** The dashboard shall display:
  - Submission progress bar (submitted / enrolled count)
  - Per-team average Likert scores (updating live)
  - A list of students who have NOT submitted (toggleable for privacy)
  - Time elapsed since session opened

### Summary and Export

- **FR-26:** The session summary view shall display:
  - Per-team aggregated Likert scores (mean, median, standard deviation, histogram)
  - All free-text comments grouped by team, anonymized (no student names visible to the presenting team). Instructor can toggle comments off for the presenting team's view to protect anonymity in small teams.
  - Instructor's own feedback and scores (entered through a privileged form)
  - Instructor-assigned presentation quality grade per presenting team
  - Participation matrix: which students completed feedback for which teams
  - Late submission flags with penalty percentages

- **FR-27:** Exports shall be available in CSV and XLSX format. The XLSX export shall include:
  - Sheet 1: Per-student participation and penalty summary
  - Sheet 2: Audience feedback raw responses
  - Sheet 3: Peer feedback raw responses
  - Sheet 4: Instructor feedback and presentation quality grades per team

### Notifications

- **FR-28:** The system shall send email notifications to the instructor and assigned TAs when:
  - A late submission is received (batched every 15 minutes to avoid spam)
  - A session deadline passes with students who have not submitted
- **FR-29:** Email delivery shall use a transactional email service (SendGrid or AWS SES).

---

## 5. Non-Goals (Out of Scope)

- **Canvas LMS integration:** The platform will not push grades to Canvas. Export is manual (CSV/XLSX).
- **Video/audio recording:** No in-class recording or media upload features.
- **Plagiarism detection:** Free-text responses are not checked for plagiarism.
- **Student-to-student visibility:** Students shall never see other students' feedback (except aggregated anonymous summaries shared by the instructor).
- **Mobile native apps:** The platform is a responsive web app only; no iOS/Android native apps.
- **Rubric-based auto-grading of presentation quality:** The system collects feedback but does not auto-assign presentation quality grades. That remains the instructor's judgment.
- **Chat or discussion features:** No in-app messaging between students or between students and instructors.
- **Historical analytics across semesters:** V1 does not provide cross-term trending or longitudinal analysis.
- **SSO/SAML integration:** V1 uses Google OAuth and email OTP only. University SSO is a future consideration.
- **Offline mode:** Students must have an internet connection to submit feedback.
- **Student-facing feedback received view:** V1 does not show presenters the aggregated feedback they received. The instructor is the sole conduit for sharing results with presenting teams.
- **Bulk/recurring session creation:** V1 requires manual session creation per class meeting. Bulk and recurring session creation is deferred to V2.
- **Student submission reminders:** V1 does not send reminder notifications to students before deadlines.

---

## 6. Design Considerations

### User Interface

**Student Mobile View (QR scan landing — multi-page flow):**

Each target (team or peer) is its own page. Progress is saved server-side on each "Next" tap.

```
Page 1 of 3: Audience → Team Alpha
+----------------------------------+
|  [Course Name] - [Session Date]  |
|  Progress: [===>    ] 1 of 3     |
+----------------------------------+
|                                  |
|  AUDIENCE FEEDBACK               |
|  Team Alpha                      |
|  Q1: Content clarity   [1-5]    |
|  Q2: Delivery          [1-5]    |
|  Q3: Comments          [____]   |
|                                  |
|      [ SAVE & NEXT → ]          |
+----------------------------------+

Page 2 of 3: Audience → Team Beta
+----------------------------------+
|  Progress: [======> ] 2 of 3     |
+----------------------------------+
|                                  |
|  AUDIENCE FEEDBACK               |
|  Team Beta                       |
|  Q1: Content clarity   [1-5]    |
|  Q2: Delivery          [1-5]    |
|  Q3: Comments          [____]   |
|                                  |
|  [ ← BACK ]  [ SAVE & NEXT → ]  |
+----------------------------------+

Page 3 of 3: Peer → Alice Smith (if presenter)
+----------------------------------+
|  Progress: [========>] 3 of 3    |
+----------------------------------+
|                                  |
|  PEER FEEDBACK                   |
|  Alice Smith                     |
|  Q1: Contribution      [1-5]    |
|  Q2: Comments          [____]   |
|                                  |
|  [ ← BACK ]  [ SAVE & FINISH ]  |
+----------------------------------+
```

**Instructor Live Dashboard:**

```
+-----------------------------------------------+
| Session: Learning Team Debates - Feb 23, 2026  |
| Section A | Deadline: 11:59 PM | Elapsed: 4m 32s|
+-----------------------------------------------+
| Submissions: [=========>      ] 23/35 (66%)    |
+-----------------------------------------------+
| Team Alpha          | Team Beta               |
| Avg Score: 4.2/5    | Avg Score: 3.8/5        |
| +-+-+-+-+-+         | +-+-+-+-+-+              |
| | |#|#|#| |         | | |#|#| | |              |
| +-+-+-+-+-+         | +-+-+-+-+-+              |
|  1 2 3 4 5          |  1 2 3 4 5               |
+-----------------------------------------------+
| [View Summary]  [View Not Submitted]           |
+-----------------------------------------------+
```

### User Experience

**Journey 1: Student Submits Audience Feedback**
1. Student scans QR code projected on screen
2. Browser opens session URL; Google OAuth prompt appears (or email entry; instructor manual verify as fallback)
3. System validates enrollment; displays multi-page feedback form (one page per target team/peer)
4. Student completes feedback for the first team, taps "Save & Next" — responses are saved server-side
5. Student repeats for each subsequent team/peer; progress bar shows completion
6. After the final page, student taps "Save & Finish"; confirmation screen with timestamp appears
7. Student can return within 7 days to edit any page via "My Submissions"

**Journey 2: Instructor Runs a Session**
1. Instructor logs in, navigates to section, creates a new session
2. Selects presentation type and assigns presenting team(s)
3. Clicks "Generate QR Code"; projects it in class
4. Opens live dashboard on their laptop
5. Monitors submissions in real time
6. Opens summary view at any time to begin debrief (session continues accepting submissions until deadline)
7. Adds instructor feedback, exports data

**Error States:**
- Student not enrolled: "You are not enrolled in this section. Contact your instructor."
- Past deadline: "The on-time submission window has passed. You can still submit until [deadline + 7 days] but a late penalty will apply."
- Past 7-day window: "The submission window for this session has closed."
- Network failure during submit: Retry button shown while the page remains open. No offline persistence across page refreshes in v1.

### Accessibility

- All form inputs shall have associated `<label>` elements
- Likert scales shall be operable via keyboard (arrow keys)
- Color is not the sole indicator of status (icons + text supplement color)
- Minimum contrast ratio of 4.5:1 for all text

---

## 7. Technical Considerations

### Architecture

```
[Student Phone]  -->  [Vercel: React SPA]  -->  [Railway: FastAPI]  -->  [Railway: PostgreSQL]
                                               [Railway: Redis] (WebSocket pub/sub)
[Instructor Laptop]  -->  [Vercel: React SPA]  -->  (same FastAPI)
```

**Backend (FastAPI on Railway):**
- `app/main.py` -- FastAPI app entry point, CORS, middleware
- `app/models/` -- SQLAlchemy ORM models
  - `user.py` -- User model (email PK, role, OAuth tokens)
  - `course.py` -- Course, Section, Enrollment models
  - `team.py` -- Team, TeamMembership models
  - `survey.py` -- PresentationType, SurveyTemplate, Question models
  - `session.py` -- Session, QRCode models
  - `feedback.py` -- Submission, Response, SubmissionVersion models
- `app/routers/` -- API route handlers
  - `auth.py` -- Google OAuth + email OTP endpoints
  - `courses.py` -- Course/section CRUD
  - `teams.py` -- Team management
  - `templates.py` -- Survey template CRUD
  - `sessions.py` -- Session lifecycle + QR generation
  - `feedback.py` -- Submission endpoints
  - `dashboard.py` -- Live dashboard data + WebSocket
  - `exports.py` -- CSV/XLSX export
- `app/services/` -- Business logic
  - `participation.py` -- Participation credit calculation
  - `penalties.py` -- Late penalty calculation
  - `notifications.py` -- Email notification service
- `app/ws/` -- WebSocket manager (Socket.IO)
- `alembic/` -- Database migrations

**Frontend (React + TypeScript on Vercel):**
- `src/pages/` -- Route-based page components
  - `StudentFeedback.tsx` -- QR code landing + feedback form
  - `InstructorDashboard.tsx` -- Live dashboard
  - `SessionSummary.tsx` -- Post-session summary
  - `CourseManagement.tsx` -- Course/section/team admin
  - `TemplateEditor.tsx` -- Survey template configuration
  - `MySubmissions.tsx` -- Student submission history + edit
  - `ExportView.tsx` -- Export configuration and download
- `src/components/` -- Reusable UI components
  - `LikertScale.tsx`, `FreeTextInput.tsx`, `QRCodeDisplay.tsx`, etc.
- `src/hooks/` -- Custom hooks
  - `useWebSocket.ts` -- Live dashboard connection
  - `useAuth.ts` -- Google OAuth + email fallback
- `src/api/` -- API client (axios/fetch wrappers)

### Data

**Core Tables:**

```sql
CREATE TABLE users (
    email VARCHAR(320) PRIMARY KEY,
    display_name VARCHAR(200),
    google_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    term VARCHAR(50) NOT NULL,
    created_by VARCHAR(320) REFERENCES users(email),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    UNIQUE(course_id, name)
);

CREATE TABLE enrollments (
    section_id UUID REFERENCES sections(id) ON DELETE CASCADE,
    student_email VARCHAR(320) REFERENCES users(email),
    role VARCHAR(20) DEFAULT 'student',  -- 'student', 'ta', 'instructor'
    PRIMARY KEY (section_id, student_email)
);

CREATE TABLE presentation_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE survey_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    presentation_type_id UUID REFERENCES presentation_types(id),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES survey_templates(id) ON DELETE CASCADE,
    question_text VARCHAR(500) NOT NULL,
    question_type VARCHAR(20) NOT NULL,  -- 'likert_5', 'likert_7', 'free_text', 'multiple_choice'
    category VARCHAR(20) NOT NULL,       -- 'audience', 'peer', 'instructor'
    options JSONB,
    is_required BOOLEAN DEFAULT TRUE,
    sort_order INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID REFERENCES sections(id) ON DELETE CASCADE,
    presentation_type_id UUID REFERENCES presentation_types(id),
    name VARCHAR(200) NOT NULL
);

CREATE TABLE team_memberships (
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    student_email VARCHAR(320) REFERENCES users(email),
    PRIMARY KEY (team_id, student_email)
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id UUID REFERENCES sections(id),
    presentation_type_id UUID REFERENCES presentation_types(id),
    template_snapshot_id UUID REFERENCES survey_templates(id),
    session_date DATE NOT NULL,
    deadline TIMESTAMPTZ NOT NULL,
    status VARCHAR(10) DEFAULT 'open',  -- 'open', 'closed' (auto-closed at deadline)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE session_teams (
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id),
    PRIMARY KEY (session_id, team_id)
);

CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    student_email VARCHAR(320) REFERENCES users(email),
    target_team_id UUID REFERENCES teams(id),
    target_student_email VARCHAR(320),  -- NULL for audience feedback, set for peer feedback
    feedback_type VARCHAR(20) NOT NULL, -- 'audience', 'peer', 'instructor'
    responses JSONB NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    is_late BOOLEAN DEFAULT FALSE,
    penalty_pct INTEGER DEFAULT 0,
    UNIQUE(session_id, student_email, target_team_id, target_student_email, version)
);

CREATE INDEX idx_submissions_session ON submissions(session_id);
CREATE INDEX idx_submissions_student ON submissions(student_email);
CREATE INDEX idx_submissions_late ON submissions(session_id, is_late) WHERE is_late = TRUE;
```

### APIs

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/google` | Google OAuth callback; returns JWT |
| `POST` | `/api/v1/auth/otp/request` | Request email OTP |
| `POST` | `/api/v1/auth/otp/verify` | Verify OTP; returns JWT |
| `GET` | `/api/v1/courses` | List courses for authenticated user |
| `POST` | `/api/v1/courses` | Create a course |
| `POST` | `/api/v1/courses/{id}/sections` | Create a section |
| `POST` | `/api/v1/sections/{id}/enroll` | Bulk enroll students (CSV body) |
| `GET` | `/api/v1/sections/{id}/roster` | Get section roster |
| `POST` | `/api/v1/courses/{id}/presentation-types` | Create presentation type |
| `PUT` | `/api/v1/presentation-types/{id}/template` | Update survey template |
| `POST` | `/api/v1/sections/{id}/teams` | Create a team |
| `POST` | `/api/v1/sessions` | Create a session + generate QR code |
| `GET` | `/api/v1/sessions/{id}` | Get session details |
| `GET` | `/api/v1/sessions/{id}/qr` | Get QR code image |
| `GET` | `/api/v1/s/{uuid}` | Student-facing: get session + form data |
| `POST` | `/api/v1/s/{uuid}/submit` | Submit feedback |
| `PUT` | `/api/v1/s/{uuid}/submit` | Update feedback (within 7-day window) |
| `GET` | `/api/v1/sessions/{id}/dashboard` | Dashboard aggregation data |
| `WS` | `/ws/sessions/{id}` | WebSocket for live dashboard |
| `GET` | `/api/v1/sessions/{id}/summary` | Session summary data |
| `GET` | `/api/v1/sessions/{id}/export` | Export as CSV or XLSX (query param) |
| `GET` | `/api/v1/me/submissions` | Student's own submission history |

### Performance

- Dashboard API responses shall complete within 300ms at p95 for sections up to 100 students
- QR code generation shall complete within 500ms
- Feedback form load (after auth) shall complete within 1 second
- Database indexes on `submissions(session_id)` and `submissions(student_email)` ensure query performance
- WebSocket broadcast per submission shall occur within 200ms of commit

---

## 8. Security and Privacy

### Authentication and Authorization

- All API endpoints (except `/api/v1/auth/*` and `/api/v1/s/{uuid}` GET) require a valid JWT in the `Authorization: Bearer` header
- JWTs expire after 24 hours; refresh tokens are not used (sessions are short-lived classroom interactions)
- The `/api/v1/s/{uuid}` GET endpoint is public (to load the form) but the POST (submit) endpoint requires authentication
- Role checks are enforced at the router level: instructor-only endpoints return HTTP 403 for students/TAs

### Input Validation

- All string inputs are sanitized to prevent XSS (React handles this by default; backend validates with Pydantic)
- Email inputs are validated against RFC 5322 format
- JSONB `responses` payloads are validated against the template schema (correct question IDs, valid Likert values, string length limits)
- Session UUIDs are validated as v4 UUIDs; invalid formats return 404

### Sensitive Data

- Student feedback is confidential. Individual responses are never exposed to other students.
- Free-text comments shown in summaries are anonymized (no attribution to the author visible to the presenting team). The instructor may also choose to withhold free-text comments entirely from the presenting team's view (releasing only aggregated scores), to protect anonymity in small teams where writing style could identify the author.
- The instructor and TA can see attribution for grading purposes.
- No passwords are stored (Google OAuth + OTP only).
- OTP codes are hashed (bcrypt) and expire after 10 minutes.

### FERPA Compliance

- Student educational records (grades, feedback) are only accessible to the student themselves and authorized instructors/TAs.
- Exports containing student data should be handled per institutional FERPA policies.

### Data Retention

- Course data (sessions, submissions, feedback, enrollments) shall be automatically deleted 1 year after the course term ends.
- The system shall notify the instructor 30 days before deletion, allowing them to export data before it is removed.
- Instructors may manually delete a course and all associated data at any time.

---

## 9. Testing Strategy

### Unit Tests

**Backend (pytest):**
- Penalty calculation: verify each tier boundary (0h, 24h, 48h, 72h, 7d, >7d)
- Participation credit: verify all scenarios in the participation matrix (US-9)
- Template versioning: verify snapshot isolation when templates are edited
- Enrollment validation: verify duplicate rejection, CSV parsing edge cases

**Frontend (vitest):**
- LikertScale component: renders correct number of options, keyboard navigation
- Feedback form: validates required fields, prevents double-submit
- Dashboard: mock WebSocket messages update state correctly

### Integration Tests

- Full submission flow: create session -> authenticate -> submit -> verify in dashboard
- Late submission flow: submit after deadline -> verify penalty calculation and notification trigger
- Template editing: edit template -> create new session -> verify old sessions use old template

### End-to-End Tests (Playwright)

- **E2E-1: Student Feedback Flow:**
  1. Navigate to session URL
  2. Authenticate with email OTP
  3. Complete all Likert and free-text fields for 2 teams
  4. Submit; verify confirmation screen
  5. Return to My Submissions; verify editable

- **E2E-2: Instructor Session Lifecycle:**
  1. Log in as instructor
  2. Create session, assign teams, generate QR
  3. (Simulate student submissions via API)
  4. Verify live dashboard updates
  5. Open summary view while session is still active; verify aggregated data

### Edge Cases

- Student scans QR code but is not enrolled in the section
- Student submits for only 1 of 2 presenting teams, then closes browser
- Two students submit at the exact same millisecond
- Instructor edits template while a session is open (should not affect open session)
- Student submits at 11:59:29 PM (within grace period) vs. 12:30:01 AM (late)
- Network disconnection during WebSocket stream; verify polling fallback activates

---

## 10. Dependencies and Assumptions

### Dependencies

**Backend:**
- **`fastapi`** -- Web framework; async support, Pydantic validation, OpenAPI docs
- **`sqlalchemy`** + **`alembic`** -- ORM and migrations
- **`asyncpg`** -- Async PostgreSQL driver
- **`python-jose`** -- JWT encoding/decoding
- **`python-socketio`** -- WebSocket support (Socket.IO protocol)
- **`qrcode`** + **`Pillow`** -- QR code generation as PNG
- **`openpyxl`** -- XLSX export
- **`httpx`** -- HTTP client for Google OAuth token exchange
- **`sendgrid`** -- Transactional email (late submission notifications, OTP delivery)
- **`bcrypt`** -- OTP hashing
- **`redis`** -- Pub/sub for WebSocket scaling (single-instance Redis on Railway)

**Frontend:**
- **`react`** + **`react-dom`** -- UI framework
- **`react-router-dom`** -- Client-side routing
- **`socket.io-client`** -- WebSocket client for live dashboard
- **`recharts`** -- Charts for dashboard and summary views
- **`@tanstack/react-query`** -- Server state management and caching
- **`tailwindcss`** -- Utility-first CSS
- **`react-hook-form`** + **`zod`** -- Form management and validation

### Assumptions

- Students have smartphones with internet access in the classroom
- The university allows Google OAuth (if blocked, the email OTP fallback covers this)
- Railway supports persistent WebSocket connections (confirmed for non-serverless plans)
- Class sizes are under 200 students per section
- The instructor provides the Qualtrics survey exports to populate the default templates

### Known Constraints

- Vercel's serverless functions do not support WebSockets; all WebSocket traffic routes to Railway
- Free-tier Railway has sleep-after-inactivity; a paid plan ($5/mo) is needed for reliable availability during class
- QR codes must be large enough to scan from the back of a lecture hall (recommend 400x400 px minimum at projection size)

---

## 11. Success Metrics

### Quantitative Metrics

| Metric | Target | How to Measure |
|---|---|---|
| TA time per session for feedback processing | < 5 minutes (down from ~1-2 hours) | TA self-report after 3 sessions |
| Student submission rate within deadline | > 90% of enrolled students | `submissions` table: on-time / enrolled |
| Summary view load time | < 2 seconds | Time to render summary view with full aggregation data |
| Late submission notification delivery | Within 15 minutes of submission | Email delivery timestamp vs. `submitted_at` |
| System uptime during class hours (M-F 8am-6pm) | 99.5% | Railway uptime monitoring |

### Qualitative Metrics

| Metric | How to Assess |
|---|---|
| Instructor satisfaction with debrief quality | Post-semester survey |
| Student experience with feedback form | In-app feedback prompt after first 3 submissions |
| TA confidence in grade accuracy | TA interview after 5 sessions |

---

## 12. Implementation Order

| Phase | Scope | Risk Level | Verification |
|---|---|---|---|
| **Phase 1: Core Data Model + Auth** | Database schema, migrations, user model, Google OAuth + email OTP, course/section/enrollment CRUD | Low | Unit tests pass; can create course, enroll students, authenticate |
| **Phase 2: Templates + Sessions** | Survey template CRUD, presentation types, team management, session creation, QR code generation | Low | Can create session with template, generate and scan QR code |
| **Phase 3: Feedback Submission** | Student feedback form (audience + peer), submission validation, participation tracking, late penalty auto-calculation | Medium | Full submission flow works; penalties calculated correctly at all tier boundaries |
| **Phase 4: Live Dashboard + Summary** | WebSocket infrastructure, live dashboard, real-time summary view, instructor feedback form | Medium | Dashboard updates in real time; summary shows correct aggregations |
| **Phase 5: Exports + Notifications** | CSV/XLSX export, email notifications for late submissions, "My Submissions" student view | Low | Export matches expected format; late notification emails delivered |
| **Phase 6: Polish + Deploy** | Responsive mobile UI, accessibility audit, error handling, Railway + Vercel deployment, production config | Medium | E2E tests pass; app accessible on mobile; deployed and reachable |

---

## Clarifying Questions

**Q1: [RESOLVED] No self-evaluation. Presenters only rate other team members.**

**Q2: [RESOLVED] The platform tracks presentation quality grades entered by the instructor per presenting team, alongside feedback scores. Included in summary view and exports.**

**Q3: [RESOLVED] Qualtrics exports are not available. Ship with generic default templates; instructors customize for their rubrics. Qualtrics-based templates can be added later.**

**Q4: [RESOLVED] Each course is fully siloed to its instructor. No global admin role in V1.**

**Q5: [RESOLVED] Students do not see aggregated feedback they received as presenters in V1. The instructor is the sole conduit for sharing results.**
