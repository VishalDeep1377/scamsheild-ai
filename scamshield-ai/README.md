# ScamShield AI

A full-stack suspicious-message and phishing analysis platform built with Next.js, FastAPI, PostgreSQL, SQLAlchemy, and scikit-learn.

> Security note: ScamShield provides risk indicators, not a guarantee that a message is fraudulent or safe. Never open suspicious links from the application. External reputation lookups are opt-in because submitted URLs may be shared with third-party services.

## Features

1. Message scanner: rule-based indicators plus optional trained ML classifier.
2. URL analyzer: safe, offline URL structure analysis (does not fetch or open submitted URLs).
3. Email analyzer: sender/reply-to mismatch, urgency, credential requests, and attachment filename signals.
4. Explainable risk score: evidence-based score with separate model confidence.
5. Scam category recognition: banking, job, delivery, prize, support, investment, credential theft, other.
6. Explainable findings and recommended actions.
7. Persistent scan history, search, filters, and scan detail.
8. Scam awareness academy with lessons and quizzes.
9. Scam reporting with status tracking.
10. Admin overview and report moderation (admin role required).

Also includes JWT authentication, CSV batch scanning, PDF report export, feedback, tests, and Docker Compose.

## Architecture

- `frontend/`: Next.js App Router, TypeScript, Tailwind CSS.
- `backend/`: FastAPI REST API, SQLAlchemy ORM, PostgreSQL (SQLite fallback for local quick-start).
- Detection pipeline: normalization → rule indicators → URL features → optional scikit-learn model → risk aggregation → explanation.
- No fake dashboard counters: dashboard metrics are calculated from persisted database records.

## Requirements

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or Docker)
- npm

## Quick start (Docker)

1. Copy environment files:

   ```bash
   cp .env.example .env
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```

2. Set a strong `JWT_SECRET` in `backend/.env`.
3. Start PostgreSQL and API:

   ```bash
   docker compose up --build
   ```

4. In another terminal, start the frontend:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. Open `http://localhost:3000`. API docs: `http://localhost:8000/docs`.

Docker Compose exposes PostgreSQL on `5433` to avoid conflicts with a local PostgreSQL installation. The API uses the service hostname `db`.

## Quick start (without Docker)

Backend:

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows; use cp on macOS/Linux
uvicorn app.main:app --reload --port 8000
```

For local development without PostgreSQL, set `DATABASE_URL=sqlite:///./scamshield.db` in `backend/.env`. This is a convenience fallback; use PostgreSQL for deployment.

Frontend:

```bash
cd frontend
npm install
# create .env.local with NEXT_PUBLIC_API_URL=http://localhost:8000/api
npm run dev
```

## Create the first admin

Register normally through the UI. Then promote that user directly in PostgreSQL:

```sql
UPDATE users SET role = 'admin' WHERE email = 'you@example.com';
```

Do not expose public admin registration.

## Train the optional ML model

The rule engine works without a model. To enable ML classification:

1. Obtain a properly licensed, labeled CSV dataset with columns `text` and `label`.
2. Labels should be `legitimate`, `spam`, `phishing`, or `scam`.
3. Keep the dataset out of Git if its license or contents require it.
4. Run:

   ```bash
   python -m app.ml.train --input path/to/messages.csv --text-column text --label-column label
   ```

The model is saved to `backend/app/ml/artifacts/message_model.joblib`. The API automatically loads it on startup if present. Evaluate on a held-out test set before using it. Training metrics are printed; they are not represented as live production performance.

## API overview

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/scans/message`
- `POST /api/scans/url`
- `POST /api/scans/email`
- `POST /api/scans/batch`
- `GET /api/scans`
- `GET /api/scans/{scan_id}`
- `GET /api/scans/{scan_id}/report`
- `POST /api/scans/{scan_id}/feedback`
- `GET /api/dashboard/summary`
- `GET /api/academy/lessons`
- `POST /api/academy/lessons/{lesson_id}/complete`
- `POST /api/reports`
- `GET /api/reports`
- `PATCH /api/reports/{report_id}/status` (admin)
- `GET /api/admin/overview` (admin)\n- `GET /api/admin/reports` (admin)

Interactive API documentation is available at `/docs`.

## Deployment

A practical free-tier arrangement (availability and limits change):
- Frontend: Vercel.
- Backend: Render or another container/Python host.
- Database: Neon or Supabase PostgreSQL.

Set:
- Frontend `NEXT_PUBLIC_API_URL` to the deployed backend API base, ending in `/api`.
- Backend `DATABASE_URL` to the managed PostgreSQL connection string.
- Backend `FRONTEND_ORIGINS` to the exact deployed frontend origin.
- A long random `JWT_SECRET`.
- `COOKIE_SECURE=true` only if using secure cookies; this project uses bearer tokens in browser local storage by default, so review your threat model before production.

For production, use HTTPS, managed secrets, backups, rate limiting at the edge, a proper email verification/password reset flow, security review, and retention controls. The included app is a solid portfolio implementation, not a certified security product.

## Privacy and safe handling

- Scan text is stored in your database so users can view history. Do not submit real passwords, OTPs, account numbers, or confidential emails.
- URL analysis is offline by default. It parses the URL but does not visit it.
- Uploaded attachments are not accepted or executed.
- External reputation integrations are not enabled by default.
- Add a privacy policy and retention/deletion controls before public launch.

## Tests

```bash
cd backend
pytest
```

## License

Choose and add a license before publishing. Check all third-party dataset and dependency licenses.
