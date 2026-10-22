# OluOra Deployment Guide (Waitlist MVP)

This document provides step-by-step instructions to deploy the waitlist landing page MVP to production (FastAPI backend and Next.js frontend).

---

## 1. Backend Deployment (FastAPI)

You can deploy the backend to **Render**, **Railway**, or any **VPS** hosting provider.

### Option A: Render (Fastest & Simplest)
1.  Go to the [Render Dashboard](https://dashboard.render.com/) and click **New** > **Web Service**.
2.  Connect your GitHub repository.
3.  Set the following configuration:
    *   **Name**: `oluora-backend`
    *   **Runtime**: `Python` or choose `Docker` (Render will automatically detect the `backend/Dockerfile` if you configure the root directory).
    *   **Root Directory**: `backend`
    *   **Build Command**: `pip install -r requirements.txt` (if deploying with Python runtime)
    *   **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` (if deploying with Python runtime)
4.  If deploying via **Docker**:
    *   Select **Docker** runtime. Render will read `backend/Dockerfile` and automatically run migration commands and bind to the correct port.
5.  Add the **Environment Variables** in the Render console (see list below).

### Option B: VPS (Docker)
If deploying to a Virtual Private Server (AWS, DigitalOcean, Hetzner, etc.):
1.  Ensure Docker and Git are installed.
2.  Clone the repository and CD to `backend`.
3.  Build the image:
    ```bash
    docker build -t oluora-backend .
    ```
4.  Run the container (passing environment variables):
    ```bash
    docker run -d -p 8000:8000 \
      -e ENVIRONMENT=production \
      -e DATABASE_URL="postgresql+asyncpg://..." \
      -e RESEND_API_KEY="re_..." \
      -e CORS_ORIGINS="https://your-frontend.vercel.app" \
      -e JWT_SECRET="your-jwt-secret" \
      -e GOOGLE_CLIENT_ID="your-client-id" \
      -e GOOGLE_CLIENT_SECRET="your-client-secret" \
      -e GOOGLE_REDIRECT_URI="https://your-frontend.vercel.app/auth/callback" \
      --name backend-instance \
      oluora-backend
    ```

---

## 2. Frontend Deployment (Next.js)

The frontend is optimized for **Vercel**:
1.  Go to the [Vercel Dashboard](https://vercel.com/) and click **Add New** > **Project**.
2.  Import your GitHub repository.
3.  Configure the settings:
    *   **Framework Preset**: `Next.js`
    *   **Root Directory**: `frontend`
4.  Add the following **Environment Variable** in Vercel:
    *   `NEXT_PUBLIC_API_URL`: The URL of your deployed backend (e.g. `https://oluora-backend.onrender.com`).
5.  Click **Deploy**.

---

## 3. Production Environment Variables (FastAPI Backend)

Ensure these variables are set in your backend hosting console:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Deployment environment | `production` |
| `DEBUG` | Toggle debug output | `false` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:password@host:port/dbname` |
| `EMAIL_PROVIDER` | Active email provider: `resend`, `sendbyte`, or `console` | `resend` |
| `EMAIL_FROM_NAME` | Display name in the From header | `OluOra` |
| `EMAIL_LOGO_URL` | Public https URL of the masthead brand mark | `https://www.useoluora.xyz/icons/logo.png` |
| `EMAIL_FROM_EMAIL` | Verified sender address | `hello@mailing.useoluora.xyz` |
| `EMAIL_REPLY_TO` | Reply-to address (defaults to the sender) | `hello@mailing.useoluora.xyz` |
| `FRONTEND_URL` | Public frontend origin, used for links inside emails | `https://www.useoluora.xyz` |
| `API_PUBLIC_URL` | Public backend origin, used for unsubscribe links | `https://oluora-backend.onrender.com` |
| `RESEND_API_KEY` | Resend API key (required only when `EMAIL_PROVIDER=resend`) | `re_...` |
| `RESEND_FROM_EMAIL` | Deployed/Verified sender address (legacy alias) | `hello@mailing.useoluora.xyz` |
| `SENDBYTE_API_KEY` | Sendbyte Africa key (required only when `EMAIL_PROVIDER=sendbyte`) | `sk_live_...` |
| `SENDBYTE_BASE_URL` | Sendbyte API base URL | `https://api.sendbyte.africa` |
| `EMAIL_MAX_PER_SECOND` | Bulk send throttle | `2.0` |
| `EMAIL_BULK_MAX_PER_RUN` | Hard cap per bulk send run | `200` |
| `FEEDBACK_REMINDER_MIN_AGE_DAYS` | Account age before a reminder is eligible | `3` |
| `FEEDBACK_REMINDER_COOLDOWN_DAYS` | Cooldown before re-reminding the same user | `30` |
| `INTERNAL_CRON_SECRET` | Shared secret for the internal cron endpoint (empty disables it) | *(Generate a random string)* |
| `CORS_ORIGINS` | Deployed frontend origin (allows CORS queries) | `https://your-frontend.vercel.app` |
| `JWT_SECRET` | Cryptographic secret for signing JWT cookies | *(Generate a random 32-character hex string)* |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `your-google-client-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET`| Google OAuth Secret key | `GOCSPX-your-secret-key` |
| `GOOGLE_REDIRECT_URI` | Google Auth Callback endpoint URL | `https://your-frontend.vercel.app/auth/callback` |
| `TIKTOK_BETA_EMAILS` | Comma-separated emails allowed to connect TikTok while in beta (empty hides TikTok for everyone) | `beta@yourdomain.com` |

---

## 4. Production Database Migrations

If migrations are not run automatically by the server start command:
1.  Run them manually from a terminal connected to the environment:
    ```bash
    alembic upgrade head
    ```

---

## 5. Transactional & Marketing Email

Email is sent through a swappable provider layer (`app/integrations/email/`); the
vendor is chosen by `EMAIL_PROVIDER`, so switching providers is an env change plus
a restart — no code change.

- **`resend`** (default) — requires `RESEND_API_KEY` and a verified `EMAIL_FROM_EMAIL`
  domain.
- **`sendbyte`** — Sendbyte Africa. Requires `SENDBYTE_API_KEY` and a domain verified
  in the Sendbyte dashboard. Use a sandbox key (`sk_test_`) to capture mail without
  delivering it.
- **`console`** — logs the message and sends nothing. Use this in local dev and CI.

Templates live in `backend/app/templates/emails/` (a shared branded `base.html` plus a
`.html`/`.txt` pair per email). Every send is logged to `email_messages`, and bulk runs
to `email_batches`, surfaced in the admin console under **Email**.

### What sends automatically

| Email | Trigger |
| :--- | :--- |
| Signup welcome | A new account is created (first Google sign-in) |
| Waitlist welcome | Someone joins the waitlist |
| Feedback reminder | Admin-triggered from **Admin → Email** (or the cron endpoint) |
| Waitlist broadcast | Admin-triggered from **Admin → Email** |

### Bulk sending

Both bulk senders support a dry run (preview the recipient count) before sending.
Sends are throttled to `EMAIL_MAX_PER_SECOND` and capped at `EMAIL_BULK_MAX_PER_RUN`
per run so a single blast cannot exhaust the provider's daily quota. Marketing emails
carry a signed one-click unsubscribe link and `List-Unsubscribe` headers; recipients who
opt out are excluded from future sends.

### Driving reminders from an external cron

Set `INTERNAL_CRON_SECRET`, then have a scheduler (Railway cron, GitHub Actions,
cron-job.org) call the secured endpoint:

```bash
curl -X POST "https://your-backend/api/v1/internal/email/run" \
  -H "X-Internal-Secret: $INTERNAL_CRON_SECRET"
```

The endpoint returns `503` when `INTERNAL_CRON_SECRET` is empty (disabled) and `401`
on a wrong secret. Nothing depends on the cron being wired — the admin button calls the
same service.

