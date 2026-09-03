# Deployment Guide

This guide covers deploying the Legal Metrology Compliance Checker to
production using managed platforms — **Render** for the FastAPI backend and
**Vercel** for the React frontend. No Docker, no server management, no
reverse proxy configuration required; both platforms build and run the app
natively from source.

## Table of Contents

- [Prerequisites](#prerequisites)
- [1. Supabase](#1-supabase)
- [2. Backend on Render](#2-backend-on-render)
  - [2A. Blueprint deploy (recommended)](#2a-blueprint-deploy-recommended)
  - [2B. Manual dashboard deploy](#2b-manual-dashboard-deploy-alternative)
  - [2C. After it's deployed](#2c-after-its-deployed-both-paths)
- [3. Frontend on Vercel](#3-frontend-on-vercel)
- [3-alt. Frontend on Netlify](#3-alt-frontend-on-netlify)
- [4. Wire the two together](#4-wire-the-two-together)
- [5. Post-deployment checklist](#5-post-deployment-checklist)
- [6. Updating a deployment](#6-updating-a-deployment)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- This repository pushed to GitHub (or GitLab/Bitbucket) — both Render and
  Vercel deploy by connecting to a git repo.
- A completed [Supabase](https://supabase.com) project (see the main
  [README](README.md#supabase-setup) if you haven't set one up) — Postgres
  connection string, project URL, anon key, and service role key.
- A Groq API key if you want the AI-assist layer live in production
  (optional — free at [console.groq.com/keys](https://console.groq.com/keys)).
- A [Render](https://render.com) account and a [Vercel](https://vercel.com)
  account (both have free tiers usable for a demo deployment).

## 1. Supabase

Do this once, shared by both platforms:

1. Confirm the **Session pooler** connection string works (Project Settings
   → Database → Connection String → URI tab). Don't use "Direct
   connection" — its hostname is IPv6-only and fails to resolve from many
   hosts, Render included.
2. Change `DEFAULT_ADMIN_PASSWORD` to something real before the backend's
   first boot in production — it seeds this account automatically on
   startup.
3. Keep the `service_role` key out of any frontend code or public
   repository — it belongs only in Render's environment variables.

## 2. Backend on Render

Two ways to do this: the **Blueprint** path uses the `render.yaml` already
in this repo's root and is the fastest way to get every setting right the
first time; the **manual** path is the same result done by hand through the
dashboard, useful if you want to see/adjust each setting yourself.

### 2A. Blueprint deploy (recommended)

1. Push this repository to GitHub (or GitLab/Bitbucket) if you haven't
   already — Render deploys by connecting to a git repo.
2. Go to [dashboard.render.com](https://dashboard.render.com) and sign in
   (GitHub sign-in is the quickest, since you'll connect a GitHub repo
   next anyway).
3. Click **New +** in the top right, then **Blueprint**.
4. Connect your GitHub account if prompted, then select this repository
   from the list. Render scans it and finds `render.yaml` at the repo
   root automatically.
5. Render shows a preview of the service it's about to create
   (`lm-compliance-api`, Python runtime, root directory `backend`). Click
   **Apply**.
6. Render will prompt you for every environment variable marked
   `sync: false` in `render.yaml` — these are the secrets it can't guess:

   | Variable | Where to get it |
   |---|---|
   | `DATABASE_URL` | Supabase → Project Settings → Database → Connection String → URI tab → **Session pooler** |
   | `SUPABASE_URL` | Supabase → Project Settings → Data API → Project URL |
   | `SUPABASE_ANON_KEY` | Supabase → Project Settings → API Keys → publishable/anon key |
   | `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API Keys → `service_role` secret key |
   | `DEFAULT_ADMIN_EMAIL` | Whatever email you want the seeded admin account to use |
   | `DEFAULT_ADMIN_PASSWORD` | A strong password — this account is created automatically on first boot |
   | `CORS_ORIGINS` | Leave a placeholder like `http://localhost:5173` for now — you'll update this in [step 4](#4-wire-the-two-together) once your Vercel URL exists |
   | `GROQ_API_KEY` | Optional — leave blank to skip the AI-assist layer, or paste a key from [console.groq.com/keys](https://console.groq.com/keys) |

7. Click **Create Web Service** (or **Create Resources**, depending on
   Render's current wording). It starts building immediately.
8. Watch the **Logs** tab. A first build takes several minutes — it's
   installing PyTorch and EasyOCR, which are large packages. You'll see
   `Uvicorn running on http://0.0.0.0:$PORT` once it's live.

### 2B. Manual dashboard deploy (alternative)

If you'd rather not use the Blueprint file:

1. Push this repository to GitHub if you haven't already.
2. In the Render dashboard, click **New +** → **Web Service**.
3. Connect your GitHub account and select this repository.
4. Configure the service:
   - **Name**: `lm-compliance-api` (or anything you like — this becomes
     part of the default URL).
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: at least 1 GB RAM. EasyOCR's PyTorch dependency
     needs the headroom — the smallest free tier will likely be too small
     or too slow to run OCR in reasonable time.
5. Before clicking create, scroll to **Environment Variables** and add
   each one from the table in step 2A above (same values, same sources).
6. Click **Create Web Service**. Render builds and deploys automatically.

### 2C. After it's deployed (both paths)

1. Render assigns a public HTTPS URL automatically — something like
   `https://lm-compliance-api.onrender.com`. Find it at the top of the
   service's dashboard page. No separate TLS or domain setup needed.
2. Confirm it's actually working:
   ```bash
   curl https://<your-service>.onrender.com/health
   ```
   should return `{"status":"ok"}`. Also open
   `https://<your-service>.onrender.com/docs` in a browser — you should
   see the interactive Swagger UI.
3. Check the **Logs** tab for a line like
   `Seeded default admin in Supabase: <your email>` confirming the admin
   account was created on first boot.
4. **Auto-deploy**: by default Render redeploys automatically on every push
   to the branch you connected. Toggle this under the service's
   **Settings → Build & Deploy** if you'd rather deploy manually.
5. **Custom domain** (optional): Settings → Custom Domains → add your own
   domain and follow Render's DNS instructions; it issues a free TLS
   certificate automatically.
6. **Cold starts**: on Render's free tier, a service spins down after
   inactivity. The next request wakes it up but will be slow — both from
   Render's own cold start and from EasyOCR loading its detection/
   recognition models (~100 MB, downloaded once and cached on that
   instance's disk). Upgrade to a paid "always on" plan to avoid this for
   real users.

## 3. Frontend on Vercel

1. In the Vercel dashboard: **Add New → Project**, import the same
   repository, and set:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite (auto-detected)
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
2. Before the first deploy, add an environment variable under the
   project's **Settings → Environment Variables**:

   ```
   VITE_API_BASE_URL=https://<your-render-service>.onrender.com
   ```

   Vite bakes this in at build time, so it must be set before you deploy —
   if you add it afterward, trigger a redeploy.
3. Click **Deploy**. Vercel gives you a URL like
   `https://lm-compliance.vercel.app` (or your own domain if you attach
   one under **Settings → Domains**).
4. Alternatively, from the CLI:

   ```bash
   cd frontend
   npm install -g vercel
   vercel                              # first deploy, follow the prompts
   vercel env add VITE_API_BASE_URL production
   vercel --prod                       # redeploy with the env var applied
   ```

## 3-alt. Frontend on Netlify

Equivalent option if you prefer Netlify over Vercel:

```bash
cd frontend
npm install -g netlify-cli
netlify init
netlify env:set VITE_API_BASE_URL https://<your-render-service>.onrender.com
netlify deploy --prod
```

Or connect the repo in the Netlify dashboard with **Base directory**
`frontend`, **Build command** `npm run build`, **Publish directory**
`frontend/dist`.

## 4. Wire the two together

Two settings must point at each other's **final** URLs — whichever
platform you deploy second, come back and update the first one:

| Setting | Where | Value |
|---|---|---|
| `VITE_API_BASE_URL` | Vercel/Netlify environment variable | Your Render backend's public URL |
| `CORS_ORIGINS` | Render environment variable | Your Vercel/Netlify frontend's public URL |

A mismatch here is the most common cause of a working API that the browser
refuses to call — requests appear to hang or silently fail because the
browser blocks reading a cross-origin response the backend didn't
explicitly allow. After changing either value, redeploy that service (Vercel
needs a rebuild for env var changes; Render just needs a restart, which
happens automatically when you save environment variables there).

## 5. Post-deployment checklist

- [ ] Changed `DEFAULT_ADMIN_PASSWORD` from the sample value before first boot.
- [ ] `CORS_ORIGINS` on Render lists the exact Vercel/Netlify origin,
      including `https://` and no trailing slash.
- [ ] `GET /health` returns `200` from the public Render URL.
- [ ] Signed in on the deployed frontend and ran one real scan end-to-end
      (upload → OCR → verdicts → PDF report download) to warm up EasyOCR's
      models and confirm Supabase Storage/Postgres connectivity from Render.
- [ ] Confirmed Groq calls succeed in production if `GROQ_API_KEY` is set.
- [ ] Rotated or restricted the Supabase `service_role` key if it was ever
      exposed anywhere other than Render's environment variables.

## 6. Updating a deployment

Push to the branch each platform tracks — both Render and Vercel/Netlify
redeploy automatically on push. No manual server steps required. If you
changed an environment variable rather than code, trigger a redeploy
manually from that platform's dashboard (Vercel requires this for env var
changes to take effect; Render restarts automatically).

## Troubleshooting

**`psycopg2.OperationalError: could not translate host name "db.<ref>.supabase.co"`**
The direct-connection hostname is IPv6-only. Use the Session pooler or
Transaction pooler connection string instead (Project Settings → Database →
Connection String).

**`server closed the connection unexpectedly` after the app has been idle**
Supabase's pooler recycles idle connections. This backend already sets
`pool_pre_ping=True` in `app/database.py` to handle this transparently — if
you still see it, confirm Render is running the latest deployed commit.

**Groq calls return `404 model_not_found`**
Groq's model catalog changes over time. Run
`Groq(api_key=...).models.list()` against your key and update
`GROQ_MODEL`/`GROQ_VISION_MODEL` in Render's environment variables to a
currently available model, then redeploy.

**Login "hangs" or silently fails in the browser but works via `curl`**
Almost always a CORS mismatch — the frontend's actual origin isn't in
`CORS_ORIGINS` on Render. Check the exact scheme and host (no trailing
slash) and redeploy the backend after changing it.

**First scan after deploy (or after a cold start) is very slow**
Expected — EasyOCR downloads and loads its detection/recognition models on
first use (~100 MB). This only happens once per instance's lifetime; run
one scan right after deploying to absorb this cost before real users hit it.

**Vercel build succeeds but the deployed app calls `localhost:8000`**
`VITE_API_BASE_URL` wasn't set before the build ran, or was added after the
last deploy — Vite only reads it at build time. Add/update it under
Environment Variables, then trigger a new deploy (`vercel --prod` or a new
push).
