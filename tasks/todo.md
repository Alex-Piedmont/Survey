# Phase 6: Polish + Deploy

## Scope
Fix remaining PRD gaps, add student role detection, default templates, Alembic migrations, and general hardening.

## Verification Criteria
- Student role detection works in GET /api/v1/s/{uuid} (presenter vs audience)
- Default templates seeded for three presentation types (FR-11)
- Alembic initial migration created and runnable
- /me/submissions returns latest versions only
- Instructor manual verify endpoint works (FR-2a)
- All tests pass

---

## Tasks

### 1. Student Role Detection
- [ ] Update `GET /api/v1/s/{uuid}` to detect student_role and student_team_id from auth (optional auth)

### 2. Default Templates (FR-11)
- [ ] `app/services/seed.py` — Seed default templates for Strategic Headlines, Learning Team Debates, Class Strategy Project
- [ ] Startup hook or CLI command to run seeds

### 3. Instructor Manual Verify (FR-2a)
- [ ] `POST /api/v1/sections/{id}/verify-student` — Instructor grants session token to student without OTP

### 4. /me/submissions Latest Only
- [ ] Fix `GET /api/v1/me/submissions` to return latest version per target only

### 5. Alembic Migration
- [ ] Generate initial migration from current models
- [ ] Verify migration runs cleanly

### 6. Tests
- [ ] Test student role detection (presenter vs audience)
- [ ] Test instructor manual verify
- [ ] Test /me/submissions latest-only behavior

---

## Review
(To be filled after implementation)
