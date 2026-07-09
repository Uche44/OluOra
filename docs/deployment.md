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
| `RESEND_API_KEY` | Resend API key for waitlist emails | `re_...` |
| `RESEND_FROM_EMAIL` | Deployed/Verified sender address | `hello@mailing.useoluora.xyz` |
| `CORS_ORIGINS` | Deployed frontend origin (allows CORS queries) | `https://your-frontend.vercel.app` |
| `JWT_SECRET` | Cryptographic secret for signing JWT cookies | *(Generate a random 32-character hex string)* |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `your-google-client-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET`| Google OAuth Secret key | `GOCSPX-your-secret-key` |
| `GOOGLE_REDIRECT_URI` | Google Auth Callback endpoint URL | `https://your-frontend.vercel.app/auth/callback` |

---

## 4. Production Database Migrations

If migrations are not run automatically by the server start command:
1.  Run them manually from a terminal connected to the environment:
    ```bash
    alembic upgrade head
    ```
