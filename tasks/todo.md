# Phase 5: Exports + Notifications

## Scope
CSV/XLSX export of session data, email notification service for late submissions, and any remaining endpoint gaps.

## Verification Criteria
- CSV export returns correct data with proper columns
- XLSX export has 4 sheets: participation summary, audience responses, peer responses, instructor feedback/grades
- Export is filterable by section/presentation type
- Notification service stubs SendGrid integration (testable without live email)
- All tests pass

---

## Tasks

### 1. Export Service
- [ ] `app/services/exports.py` — Build CSV and XLSX exports
  - Sheet 1: Per-student participation and penalty summary
  - Sheet 2: Audience feedback raw responses
  - Sheet 3: Peer feedback raw responses
  - Sheet 4: Instructor feedback and presentation quality grades

### 2. Export Router
- [ ] `GET /api/v1/sessions/{id}/export?format=csv` — CSV download
- [ ] `GET /api/v1/sessions/{id}/export?format=xlsx` — XLSX download

### 3. Notification Service
- [ ] `app/services/notifications.py` — Late submission email alerts
  - Stub SendGrid integration (env var controlled)
  - Notify instructor + TAs on late submissions
- [ ] Hook into feedback router to trigger on late submission

### 4. Tests
- [ ] `tests/test_exports.py` — CSV/XLSX content validation
- [ ] `tests/test_notifications.py` — Notification triggers (mocked email)

---

## Review
(To be filled after implementation)
