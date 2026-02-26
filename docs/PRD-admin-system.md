# PRD: Platform Administration System

**Version:** 1.0
**Date:** 2026-02-26
**Author:** Product Management
**Status:** Draft
**Project:** Classroom Survey Platform

---

## 1. Introduction / Overview

The Classroom Survey Platform currently has no concept of a platform-level administrator. Access control is entirely section-scoped via the `enrollments` table, where users hold `student`, `ta`, or `instructor` roles within individual sections. Any authenticated user can create a course and become its instructor. There is no way to govern who is allowed to create courses, view platform-wide data, or manage instructors across the system.

This PRD introduces a platform administration layer. Admins operate above the course level: they control which users can act as instructors, manage instructor-TA relationships, view all platform data, and (once password-based auth is implemented) reset user passwords. The system bootstraps with a single admin (Alex) and supports admin-to-admin promotion for future growth.

This feature is critical for moving beyond a single-instructor prototype to a multi-instructor deployment where the platform owner needs oversight and control over who can create and manage courses.

---

## 2. Goals

- **Establish platform governance:** Introduce a global admin role that controls instructor access, independent of per-section enrollment roles.
- **Bootstrap with a single admin:** Seed the database with Alex as the initial admin, with the ability to create additional admins.
- **Control instructor creation:** Only admins can grant or revoke instructor privileges. Users without instructor privileges cannot create courses.
- **Support TA management:** Admins can assign TAs under instructors, giving TAs equivalent section-level rights within the instructor's courses.
- **Provide full data visibility:** Admins can view all courses, sections, enrollments, sessions, submissions, and feedback across the entire platform.
- **Enable future password reset:** The admin model supports a password reset capability that activates once password-based auth is added.

### What Success Looks Like

Alex logs into the platform and sees an admin dashboard listing all instructors, their courses, and platform-wide statistics. A new professor requests access; Alex creates an instructor record for their email. The professor logs in and can now create courses. Alex assigns two TAs under the professor. Later, a professor leaves the university; Alex revokes their instructor status, and their ability to create new courses is disabled (existing courses remain accessible in read-only mode). Alex can drill into any course to view sessions, submissions, and feedback without needing to be enrolled.

---

## 3. User Stories

### US-1: Bootstrap Admin Account

**As the** platform owner, **I want** the system to have a pre-configured admin account (Alex), **so that** there is always at least one admin who can manage the platform from day one.

**Acceptance Criteria:**
- [ ] A database migration seeds an admin record for `alex@aptuslearning.ai`
- [ ] Alex can access admin-only endpoints and UI without manual database edits
- [ ] The seed is idempotent (running the migration twice does not create duplicates)

### US-2: Admin Manages Other Admins

**As an** admin, **I want to** promote other users to admin and revoke admin access, **so that** platform governance can be shared.

**Acceptance Criteria:**
- [ ] Admin can grant admin role to any existing user by email
- [ ] Admin can revoke admin role from another admin
- [ ] The system prevents removing the last admin (at least one admin must always exist)
- [ ] Admin role changes take effect immediately on the next API request

### US-3: Admin Manages Instructors

**As an** admin, **I want to** add, remove, and modify instructor privileges, **so that** only authorized users can create and manage courses.

**Acceptance Criteria:**
- [ ] Admin can grant instructor privileges to a user by email
- [ ] If the user does not exist yet, the system creates a user record with that email
- [ ] Admin can revoke instructor privileges; the user can no longer create new courses
- [ ] Revoking instructor privileges puts existing courses into read-only mode for the revoked instructor (no new sessions, no template edits, no enrollment changes)
- [ ] Students and TAs enrolled in the revoked instructor's courses can still submit feedback to open sessions
- [ ] Admin can view a list of all instructors with their associated courses

### US-4: Admin Manages TAs Under Instructors

**As an** admin, **I want to** assign TAs with equivalent section-level rights under a specific instructor, **so that** TAs can help manage courses without needing individual admin attention per section.

**Acceptance Criteria:**
- [ ] Admin can assign a user as a TA under an instructor
- [ ] The TA gains `ta` enrollment role in all current sections of the instructor's courses
- [ ] When the instructor creates a new section, TAs assigned under that instructor are auto-enrolled
- [ ] Admin can remove a TA from an instructor; the TA loses their `ta` enrollment role but remains enrolled in the instructor's sections (demoted to `student` role) so they do not lose access to data they may have contributed
- [ ] Removed TAs can no longer access TA-level features (roster view, feedback exports, dashboard) in those sections
- [ ] Instructor-level TAs are visually distinguished from section-level TAs in the roster

### US-5: Admin Views All Platform Data

**As an** admin, **I want to** view all courses, sections, sessions, and submissions across the platform, **so that** I have full oversight without needing to be enrolled in each course.

**Acceptance Criteria:**
- [ ] Admin dashboard shows a list of all courses with instructor, term, section count, and student count
- [ ] Admin can drill into any course to see sections, sessions, and submissions
- [ ] Admin can view any session's dashboard and summary as if they were the instructor
- [ ] Admin access bypasses enrollment checks on all read endpoints

### US-6: Admin Resets User Passwords (Future)

**As an** admin, **I want to** reset a user's password, **so that** locked-out users can regain access.

**Acceptance Criteria:**
- [ ] Admin can trigger a password reset for any user by email
- [ ] The reset mechanism sends a reset link or generates a temporary password (implementation deferred until password auth exists)
- [ ] This feature is gated behind a feature flag until password-based auth is implemented

---

## 4. Functional Requirements

### Global Role Model

- **FR-1:** Add an `is_admin` boolean column to the `users` table, defaulting to `false`. This is a platform-level attribute, independent of section-scoped enrollment roles.

- **FR-2:** Add an `is_instructor` boolean column to the `users` table, defaulting to `false`. Only users with `is_instructor = true` can create courses.

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `is_admin` | boolean | Yes | `false` | Platform-level admin flag |
| `is_instructor` | boolean | Yes | `false` | Controls ability to create courses |

- **FR-3:** The course creation endpoint (`POST /api/v1/courses`) shall check `is_instructor = true` before allowing course creation. Return HTTP 403 with message "Instructor privileges required" if the user is not an instructor.

- **FR-4:** Existing instructors (users who have created courses or hold `instructor` enrollment roles) shall be migrated to `is_instructor = true` in the same migration that adds the column.

### Instructor-TA Relationships

- **FR-5:** Create a new `instructor_tas` table to model admin-managed TA assignments at the instructor level:

| Field | Type | Required | Notes |
|---|---|---|---|
| `instructor_email` | VARCHAR(320), FK to users | PK | The instructor |
| `ta_email` | VARCHAR(320), FK to users | PK | The assigned TA |
| `created_at` | TIMESTAMPTZ | Yes | When the assignment was made |
| `created_by` | VARCHAR(320), FK to users | Yes | Which admin made the assignment |

- **FR-6:** When an admin assigns a TA under an instructor, the system shall create new enrollment records with `role = 'ta'` in all sections of courses where `courses.created_by = instructor_email`. TAs are always added separately and are never promoted from existing student enrollments. TAs cannot create courses.

- **FR-7:** When an instructor creates a new section in any of their courses, the system shall auto-enroll all TAs from the `instructor_tas` table into that section with `role = 'ta'`.

### JWT Claims

- **FR-4a:** The JWT payload shall include `is_admin` and `is_instructor` boolean claims alongside the existing `sub` (email) and `exp` claims. This avoids a database lookup on every admin/instructor-gated request. Example payload:

```json
{
  "sub": "alex@aptuslearning.ai",
  "is_admin": true,
  "is_instructor": true,
  "exp": 1709000000
}
```

- **FR-4b:** When admin or instructor flags are changed via admin endpoints, the change takes effect on the user's **next login** (next JWT issued). The current JWT remains valid until expiration. This is standard practice -- forcing token revocation would require a token blacklist, which is out of scope.

- **FR-4c:** The `/api/v1/auth/otp/verify` and `/api/v1/auth/google` endpoints shall include `is_admin` and `is_instructor` in both the JWT payload and the login response body, so the frontend can conditionally render admin/instructor UI without an additional API call.

### Instructor Revocation Behavior

- **FR-4d:** When an instructor's `is_instructor` flag is set to `false`, the instructor's existing courses enter read-only mode **for the revoked instructor only**. Specifically:
  - The revoked instructor cannot create new courses, sections, sessions, or presentation types
  - The revoked instructor cannot edit survey templates or manage enrollments
  - The revoked instructor can still view their existing courses, sessions, and summaries
  - Students and TAs enrolled in those courses are unaffected -- open sessions continue accepting submissions, TAs retain their access
  - The `instructor_tas` records under the revoked instructor are preserved (TAs keep their enrollments and TA roles in existing sections)

### Admin API Endpoints

- **FR-8:** All admin endpoints shall be prefixed with `/api/v1/admin/` and require the requesting user to have `is_admin = true`. Return HTTP 403 for non-admins.

- **FR-9:** Admin endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/admin/dashboard` | Platform overview stats |
| `GET` | `/api/v1/admin/users` | List all users with roles and course counts |
| `GET` | `/api/v1/admin/users/{email}` | Get user detail with all enrollments |
| `PATCH` | `/api/v1/admin/users/{email}/admin` | Grant or revoke admin role |
| `GET` | `/api/v1/admin/instructors` | List all instructors with their courses |
| `POST` | `/api/v1/admin/instructors` | Grant instructor privileges to a user |
| `DELETE` | `/api/v1/admin/instructors/{email}` | Revoke instructor privileges |
| `GET` | `/api/v1/admin/instructors/{email}/tas` | List TAs under an instructor |
| `POST` | `/api/v1/admin/instructors/{email}/tas` | Assign TA under an instructor |
| `DELETE` | `/api/v1/admin/instructors/{email}/tas/{ta_email}` | Remove TA from instructor |
| `GET` | `/api/v1/admin/courses` | List all courses (all instructors) |
| `GET` | `/api/v1/admin/courses/{course_id}` | Full course detail (sections, sessions, stats) |
| `POST` | `/api/v1/admin/users/{email}/reset-password` | Reset user password (future, returns 501 until password auth exists) |

### Admin Dashboard Data

- **FR-10:** The `GET /api/v1/admin/dashboard` endpoint shall return:

```json
{
  "total_users": 342,
  "total_instructors": 8,
  "total_admins": 2,
  "total_courses": 12,
  "total_active_sessions": 3,
  "total_submissions": 4521,
  "recent_courses": [...]
}
```

### Admin Read Access

- **FR-11:** Admin users shall bypass enrollment checks on all read-only endpoints. The existing `get_current_user` dependency shall be extended with an admin check: if `is_admin = true`, skip enrollment validation for GET requests to course, section, session, dashboard, and summary endpoints.

### Seed Migration

- **FR-12:** The Alembic migration that adds `is_admin` and `is_instructor` columns shall also execute a data migration to set `is_admin = true` and `is_instructor = true` for `alex@aptuslearning.ai`, and `is_instructor = true` for all users who have created at least one course or hold an `instructor` enrollment role.

---

## 5. Non-Goals (Out of Scope)

- **Password-based authentication:** This PRD adds the admin model and a stub endpoint for password reset, but does not implement password auth itself.
- **Admin audit logging:** Tracking admin actions (who granted/revoked what, when) is deferred. The `created_by` field on `instructor_tas` provides minimal traceability.
- **Admin-initiated course creation:** Admins manage who can create courses but do not create courses on behalf of instructors.
- **Admin course deletion:** Admins do not manually delete courses. Courses follow the existing automatic data retention policy (~16 months after term ends).
- **Bulk user import by admin:** Admins manage instructors and their TAs individually; bulk CSV import of instructors is deferred.
- **Role hierarchy enforcement across all endpoints:** This PRD focuses on admin CRUD and read access. Fine-grained write permissions (e.g., admin editing an instructor's survey template) are deferred.
- **Admin notifications:** No email notifications for admin actions in V1.
- **Platform settings UI:** No admin-configurable platform settings (e.g., default penalty tiers, max class size).
- **User deactivation/suspension:** Revoking instructor privileges prevents new course creation but does not lock the user out of the platform entirely.

---

## 6. Design Considerations

### User Interface

**Admin Dashboard (top-level view):**

```
+--------------------------------------------------+
| ADMIN DASHBOARD                          [Alex]  |
+--------------------------------------------------+
| Users: 342  | Instructors: 8  | Courses: 12     |
| Admins: 2   | Active Sessions: 3                |
+--------------------------------------------------+
|                                                  |
| INSTRUCTORS                     [+ Add Instructor]|
| +----------------------------------------------+ |
| | Dr. Smith (smith@univ.edu)                    | |
| | Courses: MGMT 481, FIN 301  | TAs: 2        | |
| | [Manage TAs]  [View Courses]  [Revoke]       | |
| +----------------------------------------------+ |
| | Prof. Jones (jones@univ.edu)                  | |
| | Courses: MKT 201            | TAs: 1        | |
| | [Manage TAs]  [View Courses]  [Revoke]       | |
| +----------------------------------------------+ |
|                                                  |
| ALL COURSES                                      |
| +----------------------------------------------+ |
| | MGMT 481 - Spring 2026     | Dr. Smith      | |
| | 2 sections | 45 students   | 8 sessions     | |
| | [View Details]                               | |
| +----------------------------------------------+ |
+--------------------------------------------------+
```

**Instructor TA Management Modal:**

```
+------------------------------------------+
| TAs for Dr. Smith                   [X]  |
+------------------------------------------+
| Current TAs:                             |
|   jane@univ.edu  [Remove]               |
|   bob@univ.edu   [Remove]               |
|                                          |
| Add TA: [email input______] [Add]       |
+------------------------------------------+
```

### User Experience

**Journey 1: Admin Adds an Instructor**
1. Admin navigates to Admin Dashboard
2. Clicks "+ Add Instructor"
3. Enters the instructor's email
4. System creates user record if needed, sets `is_instructor = true`
5. Instructor appears in the list
6. The instructor can now log in and create courses

**Journey 2: Admin Assigns a TA**
1. Admin clicks "Manage TAs" on an instructor card
2. Modal shows current TAs
3. Admin enters TA email and clicks "Add"
4. System creates `instructor_tas` record and auto-enrolls TA in instructor's sections
5. TA appears in the modal list and in all section rosters

**Journey 3: Admin Views Platform Data**
1. Admin clicks "View Details" on any course
2. Navigated to the standard course detail page (same as instructor view)
3. Admin can access any session dashboard or summary without enrollment

**Error States:**
- Adding an instructor who is already an instructor: "This user already has instructor privileges."
- Removing the last admin: "Cannot remove the last admin. Promote another admin first."
- Revoking instructor who has active sessions: Confirmation dialog "This instructor has N active sessions. Revoking will make their courses read-only for them. Students and TAs are unaffected. Proceed?"

### Accessibility

- Admin dashboard follows existing keyboard navigation patterns
- All action buttons have descriptive aria-labels
- Confirmation dialogs are focusable and dismissible via Escape

---

## 7. Technical Considerations

### Architecture

**New backend files:**
- `backend/app/routers/admin.py` -- Admin API endpoints
- `backend/app/models/instructor_ta.py` -- InstructorTA model
- `backend/app/services/admin.py` -- Admin business logic (instructor/TA management, data queries)

**Modified backend files:**
- `backend/app/models/user.py` -- Add `is_admin` and `is_instructor` columns
- `backend/app/routers/courses.py` -- Add `is_instructor` check to course creation
- `backend/app/routers/enrollments.py` -- Auto-enroll instructor-level TAs on section creation
- `backend/app/dependencies.py` or equivalent auth dependency -- Add admin bypass for read endpoints
- `backend/app/main.py` -- Register admin router

**New frontend files:**
- `frontend/src/pages/admin/AdminDashboardPage.tsx` -- Main admin dashboard
- `frontend/src/pages/admin/AdminInstructorsPage.tsx` -- Instructor management
- `frontend/src/pages/admin/AdminCoursesPage.tsx` -- All-courses view
- `frontend/src/pages/admin/AdminUserDetailPage.tsx` -- User detail view
- `frontend/src/components/admin/InstructorCard.tsx` -- Instructor list item
- `frontend/src/components/admin/TAManagementModal.tsx` -- TA assignment modal

**Modified frontend files:**
- `frontend/src/App.tsx` or router config -- Add `/admin/*` routes
- `frontend/src/api/client.ts` -- Add admin API methods
- Navigation component -- Add admin nav link (conditionally shown)

### Data

**New table:**

```sql
CREATE TABLE instructor_tas (
    instructor_email VARCHAR(320) REFERENCES users(email) NOT NULL,
    ta_email VARCHAR(320) REFERENCES users(email) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(320) REFERENCES users(email) NOT NULL,
    PRIMARY KEY (instructor_email, ta_email)
);
```

**Altered table:**

```sql
ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN is_instructor BOOLEAN NOT NULL DEFAULT FALSE;

-- Data migration: seed admin
UPDATE users SET is_admin = TRUE, is_instructor = TRUE WHERE email = 'alex@aptuslearning.ai';

-- Data migration: existing instructors
UPDATE users SET is_instructor = TRUE
WHERE email IN (
    SELECT DISTINCT created_by FROM courses
    UNION
    SELECT DISTINCT student_email FROM enrollments WHERE role = 'instructor'
);
```

### APIs

See FR-9 for the full endpoint table. Example request/response for key endpoints:

**POST /api/v1/admin/instructors**
```json
// Request
{ "email": "smith@university.edu" }

// Response (201)
{
  "email": "smith@university.edu",
  "display_name": "Dr. Smith",
  "is_instructor": true,
  "created": false  // user already existed
}
```

**POST /api/v1/admin/instructors/{email}/tas**
```json
// Request
{ "ta_email": "jane@university.edu" }

// Response (201)
{
  "instructor_email": "smith@university.edu",
  "ta_email": "jane@university.edu",
  "sections_enrolled": 3  // number of sections auto-enrolled into
}
```

**GET /api/v1/admin/dashboard**
```json
// Response (200)
{
  "total_users": 342,
  "total_instructors": 8,
  "total_admins": 2,
  "total_courses": 12,
  "total_active_sessions": 3,
  "total_submissions": 4521,
  "recent_courses": [
    {
      "id": "uuid",
      "name": "MGMT 481",
      "term": "Spring 2026",
      "instructor_email": "smith@university.edu",
      "section_count": 2,
      "student_count": 45
    }
  ]
}
```

### Performance

- Admin dashboard queries aggregate counts across all tables; add appropriate indexes on `courses.created_by` and `enrollments.role`
- Admin user list should support pagination (default 50 per page) for platforms with many users
- Admin read-access bypass should add negligible overhead (single boolean check on the user object already in memory)

---

## 8. Security and Privacy

### Authentication and Authorization

- All `/api/v1/admin/*` endpoints require a valid JWT with `is_admin = true` in the token claims
- Admin and instructor status are encoded in the JWT to avoid per-request DB lookups; changes take effect on next login
- Admin status is checked server-side on every request; frontend hiding of admin UI is cosmetic only
- The `is_admin` and `is_instructor` flags are never settable via public API endpoints -- only through admin-specific endpoints that themselves require admin auth
- Course creation (`POST /api/v1/courses`) now requires `is_instructor = true` in addition to valid JWT

### Input Validation

- Email inputs validated against RFC 5322 format
- Admin cannot assign themselves as a TA under an instructor
- Admin cannot revoke their own admin status if they are the last admin
- All admin endpoints validate that the target user email is well-formed before database operations

### Sensitive Data

- Admin access to all platform data means admins can see all student feedback, including attributed free-text comments
- Admin actions (granting/revoking roles) should be logged once audit logging is implemented (out of scope for V1, but the data model supports adding it)

---

## 9. Testing Strategy

### Unit Tests

**Backend (pytest):**
- Admin middleware: verify 403 for non-admin users on all admin endpoints
- Instructor gate: verify course creation returns 403 for non-instructors
- Last-admin protection: verify cannot revoke admin from the sole admin
- TA auto-enrollment: verify creating instructor-TA record enrolls TA in correct sections
- Data migration: verify existing instructors are migrated correctly

### Integration Tests

- Full admin flow: seed admin -> add instructor -> instructor creates course -> admin views course
- TA cascade: admin assigns TA -> instructor creates new section -> TA is auto-enrolled
- Admin read bypass: admin accesses course/session/summary without enrollment

### End-to-End Tests (Playwright)

- **E2E-1: Admin Adds Instructor:**
  1. Log in as admin
  2. Navigate to admin dashboard
  3. Click "Add Instructor", enter email
  4. Verify instructor appears in list
  5. Log in as new instructor, verify can create course

- **E2E-2: Admin Assigns TA:**
  1. Log in as admin
  2. Open instructor's TA management
  3. Add TA email
  4. Log in as TA, verify enrolled in instructor's sections

### Edge Cases

- User is both admin and instructor (should work -- roles are independent)
- Admin revokes instructor who has courses with active sessions
- TA assigned under instructor who has zero courses (no sections to auto-enroll into)
- Admin promotes a user to instructor who was previously a student in another course
- Two admins simultaneously try to revoke each other's admin access

---

## 10. Dependencies and Assumptions

### Dependencies

**No new libraries required.** This feature uses existing infrastructure:
- SQLAlchemy + Alembic for model changes and migrations
- FastAPI dependency injection for admin auth checks
- Existing JWT auth system for authentication

### Assumptions

- Alex's email address is known and stable (used in the seed migration)
- The platform will remain small enough that a single admin dashboard page (no pagination) is sufficient initially, but pagination is included for future-proofing
- Instructor-level TA assignments are a platform admin concern, not an instructor self-service feature (instructors can still manage section-level TAs via existing enrollment endpoints)

### Known Constraints

- The `users` table uses email as PK; changing Alex's email would require a data migration
- The existing enrollment system remains the source of truth for section-level access; the admin system layers on top of it
- Until password auth is implemented, the password reset endpoint returns 501 Not Implemented

---

## 11. Success Metrics

### Quantitative Metrics

| Metric | Target | How to Measure |
|---|---|---|
| Time to onboard new instructor | Under 1 minute (admin actions only) | Admin UX timing test |
| Admin dashboard load time | Under 500ms for platforms with up to 500 users | API response time measurement |
| Unauthorized course creation attempts blocked | 100% | Monitor 403 responses on course creation endpoint |

### Qualitative Metrics

| Metric | How to Assess |
|---|---|
| Admin confidence in platform oversight | Admin self-report after 2 weeks of use |
| Instructor onboarding experience | Instructor feedback after first course creation |

---

## 12. Implementation Order

| Phase | Scope | Risk Level | Verification |
|---|---|---|---|
| **Phase 1: Data Model + Migration** | Add `is_admin`, `is_instructor` columns to `users`. Create `instructor_tas` table. Seed admin. Migrate existing instructors. | Low | Migration runs cleanly; Alex is admin; existing instructors have `is_instructor = true` |
| **Phase 2: Auth Guards** | Add instructor gate to course creation. Add admin middleware for `/admin/*` routes. Add admin bypass for read endpoints. | Low | Non-instructors get 403 on course creation; non-admins get 403 on admin endpoints; admins can read any course |
| **Phase 3: Admin API** | Implement all admin CRUD endpoints (instructors, TAs, users, dashboard stats). | Medium | All endpoints return correct data; TA auto-enrollment works |
| **Phase 4: Frontend Admin UI** | Build admin dashboard, instructor management, TA modal, all-courses view. Add admin routes and navigation. | Medium | Admin can manage instructors and TAs through the UI; can view any course |
| **Phase 5: Polish + Testing** | E2E tests, edge case handling, error messages, confirmation dialogs. | Low | All tests pass; edge cases handled gracefully |

---

## Clarifying Questions

**Q1: [RESOLVED] Admin email is `alex@aptuslearning.ai`, hardcoded in the seed migration.**

**Q2: [RESOLVED] Revoked instructors see their courses in read-only mode. Students and TAs in those courses are unaffected -- open sessions continue accepting submissions.**

**Q3: [RESOLVED] JWT includes `is_admin` and `is_instructor` claims. Changes take effect on next login (no token blacklist needed).**

**Q4: [RESOLVED] When a TA is removed from an instructor, they lose their TA role but remain enrolled as a student. They lose access to TA-level features but keep their data contributions.**

**Q5: [RESOLVED] Admin dashboard is a top-level route at `/admin`.**

**Q6: [RESOLVED] Admins do not manually delete courses. Courses are automatically deleted per the existing data retention policy (~16 months after term ends).**

**Q7: [RESOLVED] TAs are always added separately, never promoted from student enrollments. Auto-enrollment uses `courses.created_by` to find instructor's courses. TAs cannot create courses.**
