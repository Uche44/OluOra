# OluOra

**Audience Intelligence for Creators**

OluOra transforms YouTube comment sections into crystal-clear editorial insights — uncovering what your audience wants, what questions are being asked, and what content to create next.

---

## Repository Structure

```
olundi_project/
├── frontend/          # Next.js 16 · TypeScript · Tailwind CSS v4
├── backend/           # FastAPI · SQLAlchemy 2 · PostgreSQL
├── docs/              # Architecture, API spec, design system
└── screens/           # Design mockups
```

---

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- PostgreSQL 15+ (with pgvector extension)

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in your values
npm run dev
```

Runs at **http://localhost:3000**

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env               # fill in your values
uvicorn app.main:app --reload
```

Runs at **http://localhost:8000**

---

## Environment Variables

See `frontend/.env.local.example` and `backend/.env.example` for the full list of required variables.

---

## Documentation

All architecture, API design, and design system documentation lives in the [`docs/`](./docs/) directory:

| File | Purpose |
|---|---|
| `overview.md` | Product vision and goals |
| `system-design.md` | Full system architecture |
| `api-spec.md` | REST API contract |
| `backend-guide.md` | Backend coding standards |
| `frontend-design.md` | Frontend design system |
| `frontend-color.md` | Color palette and typography |
| `resource-efficient-architecture.md` | Cost and quota management strategy |
| `agents.md` | AI coding agent rules |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS v4, Framer Motion |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Database | PostgreSQL + pgvector |
| AI | Groq API (open-weight GPT-OSS models) · OpenAI-compatible |
| Email | Resend (default) · Sendbyte Africa · swappable via `EMAIL_PROVIDER` |
| Deployment | Vercel (frontend) · Railway (backend) · Neon (database) |

---

## License

Private — All rights reserved © 2024 OluOra.
