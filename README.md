# Legal Metrology Compliance Checker

An automated screening prototype that scans packaged-commodity label images and
checks them against the mandatory declarations required under the **Legal
Metrology (Packaged Commodities) Rules, 2011** (India) — net quantity, MRP,
manufacturer/packer/importer details, month & year of manufacture, consumer
care details, country of origin, and font-size/legibility requirements for
net quantity and MRP.

Built for the SIH problem statement on automated Legal Metrology compliance
checking. This is a working prototype intended to demonstrate the end-to-end
pipeline (scan → extract → validate → report → dashboard) for enforcement
officials — see "Limitations" below for what a production rollout would still
need.

## Architecture

```
frontend/  React 18 + Vite + Tailwind CSS 4 + Recharts
                │  REST (JSON / multipart), bearer auth
                ▼
backend/   FastAPI (Python)
    ├─ auth          Proxies to Supabase Auth - the frontend only ever talks
    │                to our /auth/* endpoints, which verify passwords and
    │                mint/validate sessions via Supabase under the hood, so
    │                switching identity providers didn't touch the frontend
    │                at all. Role (admin / inspector / viewer) lives in each
    │                Supabase user's app_metadata, settable only by the
    │                service role key - a user can never self-elevate.
    ├─ OCR           EasyOCR (pure-pip, no external binary) extracts text +
    │                bounding boxes from the uploaded label image
    ├─ rule engine   Deterministic regex-based matcher against the mandatory
    │                declarations table + the Second Schedule font-size table
    ├─ AI assist     Groq vision model (optional, off by default) looks at the
    │                label photo directly as a second opinion — recovers
    │                declarations OCR misread, flags visible legibility
    │                issues, and writes the report summary; it can never
    │                override a compliant/non-compliant verdict, only flag
    │                something for human review
    ├─ report        ReportLab renders a PDF compliance report per scan
    ├─ storage       Label images persisted to Supabase Storage (falls back
    │                to local disk if SUPABASE_URL isn't set) - the app
    │                works with bytes in memory throughout, never assuming
    │                a local filesystem
    └─ database      SQLAlchemy ORM → SQLite file by default (zero setup);
                     point DATABASE_URL at a Supabase/Postgres connection
                     string to move to a shared/production database with no
                     code changes
```

No Docker is used anywhere — both services run directly with a Python
virtual environment and Node.js.

### Using Supabase (required for auth; recommended for DB/storage before deploying)

1. Create a project at [supabase.com](https://supabase.com).
2. **Database**: Project Settings → Database → Connection String → URI tab.
   Use the **Session pooler** or **Transaction pooler** string, not "Direct
   connection" - Supabase's direct-connection hostname is IPv6-only, which
   fails to resolve on many networks/ISPs (`could not translate host name`).
   Paste it into `DATABASE_URL` in `backend/.env`.
3. **Auth + Storage keys**: Project Settings → Data API for the Project URL,
   and Project Settings → API Keys for the publishable/anon key and the
   `service_role` secret key. Paste into `SUPABASE_URL`,
   `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`. The storage bucket
   (`label-images` by default) is created automatically on backend startup,
   as is the default admin account (in Supabase Auth, not a local table).

Auth has no local fallback - unlike the database (SQLite) and storage
(local disk), the app cannot authenticate anyone without all three Supabase
values set, since user accounts live in Supabase Auth rather than in our own
database.

## Prerequisites

- Python 3.10+
- Node.js 18+

## Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env         # Windows: copy, macOS/Linux: cp
```

You must set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and
`SUPABASE_SERVICE_ROLE_KEY` in `.env` before the app can authenticate anyone
(see "Using Supabase" above). Optionally also:
- point `DATABASE_URL` at Supabase Postgres instead of local SQLite
- set a `GROQ_API_KEY` (free at https://console.groq.com/keys) to enable the
  AI-assist layer — the app works fully without it
- change the seeded default admin credentials

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

The first run automatically creates the database tables and seeds a default
admin account in Supabase Auth (see `.env.example` for credentials:
`admin@legalmetrology.gov.in` / `Admin@123`). API docs are at
`http://localhost:8000/docs`.

> First OCR call downloads EasyOCR's detection/recognition models
> (~100MB) — this happens once and is cached locally.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and sign in with the default admin account.
`frontend/.env` sets `VITE_API_BASE_URL` (defaults to `http://localhost:8000`).

## Using the app

1. **Sign in** as the seeded admin, or have an admin create inspector/viewer
   accounts from the **Users** page.
2. **New Scan** — upload a clear photo of a product's principal display
   panel. Optionally provide the panel's physical area (cm²) and a
   calibration factor (mm per pixel, e.g. by photographing a ruler alongside
   the label) so the font-size rule for net quantity can be checked
   precisely; without it, the system still checks presence/correctness of
   every declaration but marks font-size as "unverified" rather than failing
   it.
3. The scan result page shows every mandatory declaration, whether it was
   found, the matched OCR text, measured vs. required font height, and a
   compliant/violation verdict per rule reference — plus a downloadable PDF
   compliance report.
4. **Repository** — search/filter all past scans by product name or status,
   and re-open any report.
5. **Dashboard** — compliance rate, violation breakdown by rule, and recent
   scan activity for enforcement monitoring.

## Key files

| Path | Purpose |
|---|---|
| `backend/app/services/rules_data.py` | Digitised mandatory-declaration list & Second Schedule font-size table |
| `backend/app/services/rule_engine.py` | Applies the rules to OCR output, produces the compliant/violation verdicts |
| `backend/app/services/ocr_service.py` | EasyOCR text + bounding-box extraction |
| `backend/app/services/groq_service.py` | Optional Groq vision assist layer |
| `backend/app/services/report_generator.py` | PDF compliance report generation |
| `backend/app/services/storage_service.py` | Supabase Storage / local-disk file storage abstraction |
| `backend/app/services/supabase_auth_service.py` | Proxies login/session-verification/user-management to Supabase Auth |
| `backend/app/routers/` | REST API: auth, scans, dashboard |
| `frontend/src/pages/` | Login, Dashboard, New Scan, Scan Detail, Repository, Users |

## Limitations & next steps for a production rollout

This prototype demonstrates the pipeline end-to-end; a production system
would additionally need:

- **Legal review of the rules table** — `rules_data.py` is a simplified,
  representative digitisation of the mandatory declarations and the Second
  Schedule font-size thresholds. A Legal Metrology domain expert should
  verify every threshold and rule reference against the current gazette
  notification and amendments before enforcement use.
- **Physical scale calibration UX** — real deployments would want a
  standard reference object (ruler, ArUco marker, or a phone-camera focal
  length + distance estimate) captured with every photo, rather than a
  manually entered mm-per-pixel value, to make font-size checks reliable at
  scale.
- **Common/generic name & unit-sale-price extraction** are free-text fields
  that are hard to validate by regex alone; these are flagged for manual
  verification in this prototype and would benefit from a fine-tuned
  extraction model.
- **Row Level Security** on the `scans`/`declarations` tables if the
  database is ever queried directly (e.g. via Supabase's client libraries)
  rather than exclusively through this backend.
