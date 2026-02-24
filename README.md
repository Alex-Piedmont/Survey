# Classroom Survey Platform

A real-time classroom feedback system where students evaluate team presentations via surveys. Instructors manage courses, sections, teams, and session templates. Students scan a QR code to submit feedback. Instructors view live dashboards and export results.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (SQLite used for tests)

## Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env   # then edit with your values
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/survey` | Async PostgreSQL connection |
| `JWT_SECRET` | `change-me-in-production` | Token signing key |
| `JWT_EXPIRE_HOURS` | `24` | Token lifetime |
| `GOOGLE_CLIENT_ID` | — | Google OAuth client ID (optional) |
| `GOOGLE_CLIENT_SECRET` | — | Google OAuth secret (optional) |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origin / QR code base URL |

### Database

```bash
# Create the database
createdb survey

# Run migrations
alembic upgrade head
```

### Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Key endpoints:

- `POST /api/v1/auth/otp/request` — Request login code
- `POST /api/v1/auth/otp/verify` — Verify code, get JWT
- `/api/v1/courses`, `/api/v1/sections`, `/api/v1/teams` — Course management
- `/api/v1/sessions` — Session creation with QR codes
- `/api/v1/s/{session_id}` — Student-facing session data
- `/api/v1/sessions/{id}/dashboard` — Live dashboard
- `/api/v1/sessions/{id}/summary` — Aggregated results
- `/api/v1/sessions/{id}/export?format=csv|xlsx` — Data export
- `/ws/sessions/{session_id}` — WebSocket for live updates
- `/health` — Health check

### Run Tests

```bash
pytest
```

Tests use an in-memory SQLite database (via aiosqlite) — no PostgreSQL needed.

## Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api` and `/ws` requests to the backend at `localhost:8000`.

### Build for Production

```bash
npm run build
```

Output goes to `frontend/dist/`.

## Project Structure

```
backend/
  app/
    core/         # Config, database, auth, dependencies
    models/       # SQLAlchemy models (14 tables)
    schemas/      # Pydantic request/response schemas
    routers/      # API endpoints (auth, courses, enrollments,
                  #   surveys, teams, sessions, feedback, dashboard)
    services/     # Business logic (penalties, participation,
                  #   aggregations, exports, notifications, seed)
    ws/           # WebSocket connection manager
  alembic/        # Database migrations
  tests/          # pytest test suite

frontend/
  src/
    api/          # Fetch wrapper with JWT auth
    components/   # Shared UI (layout, likert scale, progress bar)
    context/      # Auth context provider
    pages/        # Route pages (login, student session, instructor
                  #   courses, dashboard, template editor, summary)
```
