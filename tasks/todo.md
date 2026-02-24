# Phase 4: Live Dashboard + Summary

## Scope
Instructor dashboard with real-time submission tracking, session summary with aggregated results, instructor feedback, presentation quality grades, session listing, and comment withholding.

## Verification Criteria
- Dashboard shows submission progress (X/Y submitted) and per-team averages
- Summary shows aggregated Likert scores (mean, median, std dev) and free-text comments
- Instructor can submit their own feedback scores
- Instructor can assign presentation quality grade per team
- Instructor can withhold specific comments
- WebSocket broadcasts submission events in real time
- Session listing endpoint for sections
- All tests pass

---

## Tasks

### 1. New Models
- [ ] `app/models/presentation_grade.py` — PresentationGrade (session_id, team_id, grade, comments)
- [ ] Update `app/models/__init__.py`

### 2. Aggregation Service
- [ ] `app/services/aggregations.py` — Compute per-team Likert stats (mean, median, std dev, histogram), group free-text comments, build participation matrix

### 3. Pydantic Schemas
- [ ] `app/schemas/dashboard.py` — DashboardResponse, SummaryResponse, InstructorFeedbackCreate, PresentationGradeCreate/Response, CommentWithhold

### 4. Dashboard Router
- [ ] `GET /api/v1/sessions/{id}/dashboard` — Submission progress, per-team averages, non-submitter list
- [ ] `GET /api/v1/sessions/{id}/summary` — Full aggregations, free-text comments, participation matrix, grades
- [ ] `POST /api/v1/sessions/{id}/instructor-feedback` — Instructor submits their own scores per team
- [ ] `POST /api/v1/sessions/{id}/teams/{team_id}/presentation-grade` — Assign quality grade
- [ ] `PUT /api/v1/sessions/{id}/comments/{submission_id}/withhold` — Withhold a comment
- [ ] `GET /api/v1/sections/{id}/sessions` — List sessions for a section

### 5. WebSocket
- [ ] `app/ws/manager.py` — WebSocket connection manager
- [ ] `WS /ws/sessions/{id}` — Live dashboard updates
- [ ] Update feedback router to broadcast on new submission

### 6. Tests
- [ ] `tests/test_dashboard.py` — Dashboard data, summary aggregation, instructor feedback, grades, comment withholding, session listing
- [ ] `tests/test_websocket.py` — WebSocket connection and broadcast

---

## Review
(To be filled after implementation)
