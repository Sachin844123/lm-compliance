# Legal Metrology Compliance Checker

**Automated label compliance screening for packaged commodities, under the Legal Metrology (Packaged Commodities) Rules, 2011 (India).**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?logo=tailwindcss&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Postgres%20%7C%20Auth%20%7C%20Storage-3ECF8E?logo=supabase&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Vision%20AI-F55036?logoColor=white)
![No Docker](https://img.shields.io/badge/Docker-not%20required-inactive)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Supabase Setup](#supabase-setup)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Environment Variables](#environment-variables)
- [Using the App](#using-the-app)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Compliance Rules Reference](#compliance-rules-reference)
- [Project Structure](#project-structure)
- [Limitations & Roadmap](#limitations--roadmap)
- [License](#license)

---

## Overview

Packaged commodities sold in India must carry mandatory declarations under
the **Legal Metrology (Packaged Commodities) Rules, 2011** — net quantity,
MRP, manufacturer/packer/importer details, month & year of manufacture,
consumer care information, and more, each with prescribed formatting and
minimum font-size requirements. Verifying this manually, at the scale of
India's retail market, is slow and inconsistent.

This project is a working prototype, built for the corresponding Smart India
Hackathon problem statement, that automates the first pass of that
verification: an enforcement officer photographs a product label, and the
system extracts, validates, and reports on every mandatory declaration in
seconds — with a persistent repository, dashboard, and exportable PDF
reports to support the officer's own judgment, not replace it.

## Key Features

- **Image-based label scanning** — upload a photo of a product's principal
  display panel for automated analysis.
- **OCR text & layout extraction** — detects every line of printed text on
  the label along with its position and pixel dimensions.
- **Rule-based compliance engine** — deterministic, auditable matching of
  extracted text against the mandatory declarations required by the Rules,
  including the Second Schedule font-size thresholds for net quantity and
  MRP.
- **AI-assisted second opinion** — an optional vision-language model reviews
  the label photo directly, recovering declarations OCR misread and flagging
  legibility issues a pixel measurement alone would miss. It can only add
  information for human review, never override a rule-engine verdict.
- **Digital compliance reports** — a formatted PDF report per scan, with the
  product photo, full declaration checklist, and an AI-written summary,
  generated on demand.
- **Repository & search** — every scan is retained with its full history,
  searchable by product name and filterable by compliance status.
- **Enforcement dashboard** — compliance rate, violation breakdown by rule,
  and recent scan activity at a glance.
- **Role-based access control** — admin, inspector, and viewer roles, backed
  by Supabase Auth; roles live in server-controlled metadata so a user can
  never self-elevate.
- **Cloud-ready storage** — labels persist to Supabase Storage and Supabase
  Postgres by default, with a zero-setup local fallback (SQLite + local
  disk) for development.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS 4, React Router, Recharts, Axios |
| Backend | Python, FastAPI, SQLAlchemy |
| OCR | EasyOCR (pure-pip, no external binary dependency) |
| AI assist | Groq (vision-language model) |
| PDF generation | ReportLab |
| Database | Supabase Postgres (SQLite fallback for local dev) |
| File storage | Supabase Storage (local disk fallback for local dev) |
| Authentication | Supabase Auth |
| Deployment | No Docker — runs directly via a Python virtual environment and Node.js |

## Architecture

```
┌──────────────────────┐      REST (JSON / multipart)       ┌───────────────────────────┐
│       frontend        │ ─────────────────────────────────▶ │         backend            │
│  React + Vite + Tail- │        bearer token auth            │        FastAPI (Python)    │
│  wind + Recharts       │ ◀───────────────────────────────── │                             │
└──────────────────────┘                                     └───────────────────────────┘
                                                                        │
                          ┌─────────────────────────────────────────────┼─────────────────────────────┐
                          ▼                                             ▼                             ▼
                 ┌─────────────────┐                          ┌──────────────────┐          ┌──────────────────┐
                 │   Supabase       │                          │   Supabase        │          │   Groq            │
                 │   Auth           │                          │   Postgres +      │          │   Vision model    │
                 │                  │                          │   Storage         │          │   (optional)      │
                 └─────────────────┘                          └──────────────────┘          └──────────────────┘
```

**Request pipeline for a scan:**

1. **Auth** — the frontend only ever talks to this backend's `/auth/*`
   endpoints; the backend proxies login and session verification to
   Supabase Auth, so switching identity providers never touched the
   frontend. Roles live in each Supabase user's `app_metadata`, writable
   only with the service-role key.
2. **OCR** — EasyOCR extracts every line of text on the uploaded label, with
   its bounding box and pixel height.
3. **Rule engine** — a deterministic matcher (`rule_engine.py`) checks the
   extracted text against the mandatory declarations table
   (`rules_data.py`), including a sliding-window match for declarations OCR
   splits across lines, and the Second Schedule font-size thresholds.
4. **AI assist (optional)** — if configured, Groq's vision model looks at
   the photo directly as a second opinion: recovering anything OCR missed,
   flagging visible legibility issues, and writing the report summary. It
   can only move a result from "missing" to "found" for human review — it
   never overturns a verdict the rule engine already reached.
5. **Report** — ReportLab renders a PDF compliance report on demand,
   embedding the label photo and the full declaration checklist.
6. **Storage** — the label image is persisted to Supabase Storage; the scan,
   its declarations, and verdicts are persisted to Supabase Postgres.

No Docker is used anywhere — both services run directly with a Python
virtual environment and Node.js.

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Supabase](https://supabase.com) project (free tier is sufficient)

### Supabase Setup

Authentication has no local fallback — the app cannot sign anyone in without
a configured Supabase project, since accounts live in Supabase Auth rather
than a local table. The database and file storage do have local fallbacks
(SQLite and local disk) for quick experimentation, but Supabase is
recommended for both before deploying.

1. Create a project at [supabase.com](https://supabase.com).
2. **Database** — Project Settings → Database → Connection String → URI
   tab. Use the **Session pooler** or **Transaction pooler** string, *not*
   "Direct connection" — Supabase's direct-connection hostname is
   IPv6-only, which fails to resolve on many networks
   (`could not translate host name`). Copy it into `DATABASE_URL`.
3. **Auth & Storage keys** — Project Settings → Data API for the Project
   URL, and Project Settings → API Keys for the publishable/anon key and
   the `service_role` secret key. Copy these into `SUPABASE_URL`,
   `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`.

The storage bucket and the default admin account are both created
automatically the first time the backend starts.

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env         # Windows: copy, macOS/Linux: cp
```

Fill in the Supabase values from the step above in `.env` (see
[Environment Variables](#environment-variables) for the full reference),
then start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

The first run creates the database tables and seeds a default admin account
in Supabase Auth (credentials in `.env.example`:
`admin@legalmetrology.gov.in` / `Admin@123` — change these before any real
deployment). Interactive API docs are served at `http://localhost:8000/docs`.

> The first OCR call downloads EasyOCR's detection/recognition models
> (roughly 100 MB) — a one-time download, cached locally afterward.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and sign in with the default admin account.
`frontend/.env` sets `VITE_API_BASE_URL` (defaults to
`http://localhost:8000`).

## Environment Variables

All backend configuration lives in `backend/.env` (copy from
`backend/.env.example`).

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite:///./legal_metrology.db` | SQLAlchemy connection string. Point at Supabase Postgres for a shared/production database. |
| `SUPABASE_URL` | **Yes** | — | Your Supabase project URL. Required for authentication. |
| `SUPABASE_ANON_KEY` | **Yes** | — | Publishable/anon key, used to validate user sessions. |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | — | Secret key, used for admin user-management and Storage access. Server-side only. |
| `SUPABASE_STORAGE_BUCKET` | No | `label-images` | Storage bucket for uploaded label photos; created automatically. |
| `DEFAULT_ADMIN_EMAIL` | No | `admin@legalmetrology.gov.in` | Seeded admin account email. |
| `DEFAULT_ADMIN_PASSWORD` | No | `Admin@123` | Seeded admin account password — change before deploying. |
| `DEFAULT_ADMIN_NAME` | No | `Chief Inspector` | Seeded admin account display name. |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated list of allowed frontend origins. |
| `GROQ_API_KEY` | No | — | Enables the AI-assist layer. Free at [console.groq.com/keys](https://console.groq.com/keys). The app works fully without it. |
| `GROQ_MODEL` | No | `openai/gpt-oss-120b` | Text model used for the report summary fallback. |
| `GROQ_VISION_MODEL` | No | `qwen/qwen3.6-27b` | Vision-capable model used to review the label photo directly. |

Groq's model catalog changes over time — if a model id 404s, run
`client.models.list()` against your key to see what's currently available.

`frontend/.env` sets a single variable: `VITE_API_BASE_URL`.

## Using the App

1. **Sign in** as the seeded admin, or have an admin create inspector/viewer
   accounts from the **Users** page.
2. **New Scan** — upload a clear photo of a product's principal display
   panel. Optionally provide the panel's physical area (cm²) and a
   calibration factor (mm per pixel — e.g. by photographing a ruler
   alongside the label) so the font-size rule for net quantity can be
   checked precisely. Without it, the system still checks presence and
   correctness of every declaration, but marks font-size as "unverified"
   rather than failing it.
3. **Scan Detail** shows every mandatory declaration: whether it was found,
   the matched OCR text, measured vs. required font height, and a
   compliant/violation verdict per rule reference — plus a downloadable PDF
   compliance report and the AI-assisted summary.
4. **Repository** — search and filter every past scan by product name or
   compliance status, and re-open any report.
5. **Dashboard** — compliance rate, violation breakdown by rule, and recent
   scan activity for enforcement monitoring.

## Deployment

See **[DEPLOY.md](DEPLOY.md)** for the full production deployment guide —
covers a VPS (systemd + Nginx) or Render for the backend, and Vercel/Netlify
(or static Nginx) for the frontend, plus a post-deployment checklist and
troubleshooting for the exact issues this project has hit in practice
(Supabase's IPv6-only direct connection, pooled-connection drops, CORS
origin mismatches, and Groq model catalog changes).

## API Reference

Full interactive documentation (Swagger UI) is served at `/docs` once the
backend is running. Summary of the main endpoints:

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | — | Sign in, returns a bearer token and user profile. |
| `GET` | `/auth/me` | Any role | Return the current authenticated user. |
| `POST` | `/auth/users` | Admin | Create a new user with a given role. |
| `GET` | `/auth/users` | Admin | List all users. |
| `POST` | `/scans/` | Any role | Upload a label image and run the full compliance pipeline. |
| `GET` | `/scans/` | Any role | List scans, filterable by status and searchable by product name. |
| `GET` | `/scans/{id}` | Any role | Full detail for one scan, including all declarations. |
| `GET` | `/scans/{id}/image` | Any role | The scan's label photo. |
| `GET` | `/scans/{id}/report` | Any role | Generate and download the scan's PDF compliance report. |
| `DELETE` | `/scans/{id}` | Admin, Inspector | Delete a scan and its stored image. |
| `GET` | `/dashboard/stats` | Any role | Aggregate compliance rate, violation breakdown, and recent scans. |

## Compliance Rules Reference

Declarations checked by the rule engine (`backend/app/services/rules_data.py`):

| Declaration | Rule Reference | Required |
|---|---|---|
| Name & address of manufacturer/packer/importer | Rule 6(1)(a) | Yes |
| Common/generic name of the commodity | Rule 6(1)(b) | Yes |
| Net quantity (weight/volume/number) | Rule 6(1)(c) & Rule 8 | Yes |
| Month & year of manufacture/packing/import | Rule 6(1)(d) & Rule 18 | Yes |
| Maximum Retail Price (inclusive of all taxes) | Rule 6(1)(e) & Rule 18 | Yes |
| Consumer/customer care details | Rule 6(1)(f) | Yes |
| Country of origin | Rule 6(8) / 2017 Amendment | Optional |
| Unit sale price | Rule 6(1)(e), Explanation | Optional |

Minimum numeral/letter height for the **net quantity** declaration, by
principal display panel area (Second Schedule):

| Panel Area | Minimum Height |
|---|---|
| Up to 100 cm² | 1 mm |
| 100–500 cm² | 2 mm |
| 500–2500 cm² | 4 mm |
| Above 2500 cm² | 6 mm |

> This is a simplified, representative digitisation of the Rules for the
> purpose of an automated screening prototype. See
> [Limitations & Roadmap](#limitations--roadmap).

## Project Structure

```
SIH/
├── backend/
│   ├── app/
│   │   ├── main.py                  FastAPI app entrypoint, CORS, startup seeding
│   │   ├── config.py                Environment-driven settings
│   │   ├── database.py              SQLAlchemy engine/session
│   │   ├── models.py                Scan and Declaration ORM models
│   │   ├── schemas.py               Pydantic request/response schemas
│   │   ├── deps.py                  Auth dependencies (Supabase session verification)
│   │   ├── routers/
│   │   │   ├── auth.py              Login, session, user management
│   │   │   ├── scans.py             Upload, list, detail, image, report, delete
│   │   │   └── dashboard.py         Aggregate compliance statistics
│   │   └── services/
│   │       ├── ocr_service.py             EasyOCR text + bounding-box extraction
│   │       ├── rules_data.py               Mandatory declarations & font-size table
│   │       ├── rule_engine.py               Deterministic compliance verdicts
│   │       ├── groq_service.py              Optional Groq vision AI-assist layer
│   │       ├── report_generator.py          PDF compliance report generation
│   │       ├── storage_service.py           Supabase Storage / local-disk abstraction
│   │       └── supabase_auth_service.py     Supabase Auth proxy
│   └── requirements.txt
└── frontend/
    └── src/
        ├── api/client.js             Axios instance with auth interceptor
        ├── context/AuthContext.jsx   Login/logout/session state
        ├── components/               Layout, route guard, shared UI
        └── pages/
            ├── Login.jsx
            ├── Dashboard.jsx
            ├── ScanUpload.jsx
            ├── ScanDetail.jsx
            ├── Repository.jsx
            └── Users.jsx
```

## Limitations & Roadmap

This prototype demonstrates the full pipeline end-to-end; a production
rollout would additionally need:

- **Legal review of the rules table** — `rules_data.py` is a simplified,
  representative digitisation of the mandatory declarations and Second
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
  database is ever queried directly (e.g. via Supabase client libraries)
  rather than exclusively through this backend.

## License

No license has been specified for this project yet. Add one (e.g. MIT,
Apache 2.0) before any public release if required by your use case.
