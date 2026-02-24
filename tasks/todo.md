# Phase 2: Templates + Sessions

## Status: COMPLETE — 50/50 tests passing (30 Phase 1 + 20 Phase 2)

---

## Tasks

### 1. New Models
- [x] `app/models/survey.py` — PresentationType, SurveyTemplate, Question
- [x] `app/models/team.py` — Team, TeamMembership
- [x] `app/models/session.py` — Session, SessionTeam
- [x] Updated `app/models/__init__.py`

### 2. Pydantic Schemas
- [x] `app/schemas/survey.py` — PresentationTypeCreate/Response, TemplateUpdate/Response, QuestionSchema/Response
- [x] `app/schemas/team.py` — TeamCreate/Response, TeamMemberUpdate
- [x] `app/schemas/session.py` — SessionCreate/Response, QRCodeResponse, StudentSessionResponse

### 3. Presentation Type + Template Router
- [x] `POST /api/v1/courses/{id}/presentation-types` — Creates ptype + empty v1 template
- [x] `GET /api/v1/courses/{id}/presentation-types` — List ptypes
- [x] `PUT /api/v1/presentation-types/{id}/template` — Creates new version (FR-12)
- [x] `GET /api/v1/presentation-types/{id}/template` — Returns latest version with questions

### 4. Team Management Router
- [x] `POST /api/v1/sections/{id}/teams` — Create with optional members (validates enrollment)
- [x] `GET /api/v1/sections/{id}/teams` — List teams, filter by presentation type
- [x] `PUT /api/v1/teams/{id}/members` — Replace membership list

### 5. Session + QR Code Router
- [x] `POST /api/v1/sessions` — Creates session with template snapshot + team links
- [x] `GET /api/v1/sessions/{id}` — Session details with presenting team IDs
- [x] `GET /api/v1/sessions/{id}/qr` — QR code as base64 PNG
- [x] `GET /api/v1/s/{uuid}` — Public student-facing endpoint with full form data

### 6. Tests (20 new)
- [x] `tests/test_surveys.py` — 6 tests: ptype CRUD, template versioning, question types
- [x] `tests/test_teams.py` — 6 tests: create with/without members, unenrolled rejection, list, filter, update
- [x] `tests/test_sessions.py` — 8 tests: create, deadline, QR, snapshot isolation, student endpoint

## Key Decisions
- Template snapshots use negative version numbers to distinguish from editable versions
- QR codes generated server-side with `qrcode` library, returned as base64 PNG
- Student-facing `/api/v1/s/{uuid}` GET is public (no auth), returns all form data
- Student role detection ("audience" vs "presenter") stubbed for Phase 3 (requires auth)
