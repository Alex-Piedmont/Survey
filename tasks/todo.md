# Platform Administration System

## Phase 1: Data Model + Migration
- [x] 1.1 Add `is_admin`, `is_instructor` to User model
- [x] 1.2 Create InstructorTA model
- [x] 1.3 Register InstructorTA in models/__init__.py
- [x] 1.4 Generate + edit Alembic migration with data seed
- [x] Verify: migration runs, flags set correctly

## Phase 2: Auth Guards
- [x] 2.1 Modify JWT create/verify in security.py
- [x] 2.2 Update get_current_user in deps.py
- [x] 2.3 Add require_admin dependency
- [x] 2.4 Add admin bypass to require_role
- [x] 2.5 Update auth endpoints to pass flags
- [x] 2.6 Update UserResponse schema
- [x] 2.7 Fix verify_access_token callers (sessions.py, test_auth.py)
- [x] 2.8 Instructor gate on course creation
- [x] 2.9 Admin bypass on read endpoints (courses, dashboard, enrollments)
- [x] Verify: non-instructor 403 on course create, admin reads any course

## Phase 3: Admin API
- [x] 3.1 Create admin schemas
- [x] 3.2 Create admin service layer
- [x] 3.3 Create admin router
- [x] 3.4 Register router in main.py
- [x] 3.5 TA auto-enroll on section creation
- [x] Verify: admin CRUD flow, TA auto-enrollment

## Phase 4: Frontend Admin UI
- [x] 4.1 Extend AuthContext with isAdmin/isInstructor
- [x] 4.2 Add patch to API client
- [x] 4.3 Create AdminLayout
- [x] 4.4 Create admin pages (Dashboard, Instructors, Courses)
- [x] 4.5 Create TA management modal
- [x] 4.6 Add admin routes to App.tsx
- [x] 4.7 Add admin nav link to InstructorLayout
- [x] Verify: frontend builds with no TS errors

## Phase 5: Polish + Testing
- [x] 5.1 Instructor revocation enforcement on write endpoints (create_session, create_section)
- [x] 5.2 Error handling in frontend (409, 400, 403 shown inline)
- [x] 5.3 Backend admin tests (10 tests covering auth, CRUD, edge cases)
- [x] Verify: all 127 tests pass, frontend builds clean

## Review
- All 127 backend tests pass (including 10 new admin tests)
- Frontend builds with zero TS errors
- Migration runs cleanly with data seed for admin + existing instructors
