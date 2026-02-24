# Phase 3: Feedback Submission

## Scope
Student feedback form (audience + peer), submission validation, participation tracking, late penalty auto-calculation.

## Verification Criteria
- Full submission flow works (audience + peer)
- Late penalties calculated correctly at all tier boundaries
- Participation credit is proportional (K/N)
- 7-day revision window works, submissions after 7 days rejected
- Template snapshot questions are validated against responses

---

## Tasks

### 1. Submission Model
- [ ] `app/models/submission.py` — Submission model (per PRD schema)
- [ ] Update `app/models/__init__.py`

### 2. Penalty + Participation Services
- [ ] `app/services/penalties.py` — Calculate late penalty tier from elapsed time (FR-22)
- [ ] `app/services/participation.py` — Calculate proportional participation credit (FR-20)

### 3. Pydantic Schemas
- [ ] `app/schemas/submission.py` — SubmitFeedback request, SubmissionResponse, ParticipationResponse

### 4. Update Student Session Endpoint
- [ ] Update `GET /api/v1/s/{uuid}` to determine student role (audience vs presenter) when auth is provided
- [ ] Return student's existing submissions for this session (for edit/resume)

### 5. Feedback Submission Router
- [ ] `POST /api/v1/s/{uuid}/submit` — Submit feedback for one target (per-page save, FR-16a)
  - Requires auth
  - Validates student is enrolled in the section
  - Validates target (team_id or student_email) is valid for this session
  - Auto-detects feedback_type (audience vs peer)
  - Calculates is_late and penalty_pct
  - Rejects if past 7-day window (FR-19)
- [ ] `PUT /api/v1/s/{uuid}/submit` — Update feedback (creates new version, FR-18)
  - Same validations + within 7-day window

### 6. Student Submission History
- [ ] `GET /api/v1/me/submissions` — Student's own submission history

### 7. Unit Tests
- [ ] `tests/test_penalties.py` — All penalty tier boundaries (0h, 24h, 48h, 72h, 7d, >7d)
- [ ] `tests/test_participation.py` — Proportional credit: 0/N, K/N, N/N for audience and peer
- [ ] `tests/test_submissions.py` — Full submission flow:
  - Audience submits for one team (per-page save)
  - Audience submits for all teams
  - Presenter submits peer feedback (excluding self)
  - Late submission gets correct penalty
  - Submission after 7 days rejected
  - Revision creates new version
  - Student role detection (audience vs presenter)

---

## Review
(To be filled after implementation)
