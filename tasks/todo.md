# Frontend Phase 1: Scaffolding + Auth + Student Feedback Flow

## Scope
Set up React + TypeScript + Vite project, implement auth (Google OAuth + OTP),
and build the core student feedback flow (QR scan landing → multi-page form → confirmation).

## Verification Criteria
- Vite dev server runs without errors
- Auth flow works (OTP login for dev, Google OAuth stub)
- Student can view session form via /s/{uuid}
- Multi-page feedback form with per-page server saves
- Likert scale and free-text components work
- Progress bar shows completion
- Confirmation screen after final submit

---

## Tasks

### 1. Project Scaffolding
- [ ] Vite + React + TypeScript project in /frontend
- [ ] Tailwind CSS setup
- [ ] React Router DOM routes
- [ ] API client (fetch wrapper with auth headers)
- [ ] Auth context (token storage, login/logout)
- [ ] React Query setup

### 2. Auth Pages
- [ ] Login page with email OTP flow (dev mode)
- [ ] Google OAuth button (stub for now)
- [ ] Auth state persisted in localStorage
- [ ] Protected route wrapper

### 3. Student Feedback Flow
- [ ] /s/:sessionId — Session landing page (loads session data)
- [ ] Multi-page form: one page per target team (audience) + per peer (presenter)
- [ ] LikertScale component (1-5 radio buttons)
- [ ] FreeTextInput component (textarea)
- [ ] Per-page "Save & Next" submits to backend
- [ ] Progress bar showing page X of N
- [ ] Back navigation between pages
- [ ] Final "Save & Finish" with confirmation screen

### 4. My Submissions
- [ ] /me/submissions — List student's submissions
- [ ] Link back to session for editing within 7-day window
