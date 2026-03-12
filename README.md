# Weblabs AI Lead Generator

An automated local business lead generation pipeline that discovers businesses without a modern web presence and drafts personalized outreach emails using AI.

Built as an internal tool for my freelance web development practice to automate the cold-outreach workflow end-to-end: from finding businesses on Google Maps, to generating context-aware emails, to sending them directly from a review dashboard.

## Architecture

```
Docker Compose
+-----------+-----------+-----------+------------+-----------+
|   n8n     |  Backend  | Frontend  | PostgreSQL |  Ollama   |
|  :5678    |  :8000    |  :3000    |  :5432     |  :11434   |
| Workflows |  FastAPI  |   React   |            | Local LLM |
+-----------+-----------+-----------+------------+-----------+
```

**Data flow:** n8n triggers scheduled searches via the backend API. The backend queries Google Places for businesses, stores them as leads in PostgreSQL, and generates personalized emails through OpenAI or a local Ollama instance. The React dashboard provides a review interface for approving, editing, and sending emails.

## Features

- **Automated lead search** -- Finds local businesses via Google Places API or SerpAPI with configurable radius and industry filters
- **AI email generation** -- Produces personalized outreach emails using OpenAI GPT-4o-mini or local Ollama (Llama 3.1), with three randomized style variants
- **Smart industry detection** -- Two-stage lookup: company name keyword matching first, then Google Places category mapping
- **Review dashboard** -- React UI with keyboard navigation, inline email editing, approve/reject workflow, and live stats
- **n8n workflow automation** -- Daily scheduled search at 9:00 + batch email sender with rate limiting
- **SMTP delivery** -- Direct email sending with HTML formatting and self-BCC for tracking

## Tech Stack

| Layer | Technology |
|-------|------------|
| Orchestration | Docker Compose |
| Automation | n8n |
| Backend | Python 3.11, FastAPI, SQLAlchemy, httpx |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Database | PostgreSQL 16 |
| AI | OpenAI API / Ollama (local) |
| Email | aiosmtplib |

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- (Optional) OpenAI API key for higher-quality email generation
- (Optional) Google Places API key for real business search

### Setup

```bash
cp .env.example .env
# Edit .env with your credentials

docker-compose up -d
```

### Services

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:3000 | Lead review and management |
| n8n | http://localhost:5678 | Workflow automation |
| API Docs | http://localhost:8000/docs | Interactive API documentation |

## Configuration

All configuration is done through environment variables. See `.env.example` for the full list.

Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_PASSWORD` | Yes | Database password |
| `OPENAI_API_KEY` | No | Falls back to Ollama if not set |
| `SMTP_HOST` / `SMTP_PASSWORD` | For sending | SMTP credentials |
| `GOOGLE_PLACES_API_KEY` | No | Falls back to demo data if not set |

## Project Structure

```
n8n-workflow-weblabs/
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── main.py                 # FastAPI routes and CRUD
│   ├── models.py               # SQLAlchemy models + Pydantic schemas
│   ├── database.py             # DB connection and session factory
│   ├── ai_service.py           # Email generation (OpenAI / Ollama)
│   ├── email_service.py        # Async SMTP delivery
│   ├── scraper_service.py      # Google Places / SerpAPI integration
│   └── init.sql                # Database schema and seed data
│
├── frontend/
│   └── src/
│       ├── App.tsx             # Main dashboard component
│       ├── main.tsx            # React entry point
│       └── index.css           # Tailwind base styles
│
└── n8n/
    └── workflows/
        ├── lead-generator-workflow.json
        └── email-sender-workflow.json
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/leads` | GET | List leads with pagination and filters |
| `/api/leads/{id}` | GET | Get single lead |
| `/api/leads/{id}/generate-email` | POST | Generate AI email for lead |
| `/api/leads/{id}/approve` | POST | Approve lead (with optional edit) |
| `/api/leads/{id}/reject` | POST | Reject lead |
| `/api/leads/{id}/send-email` | POST | Send email to lead |
| `/api/search` | POST | Search for new businesses |
| `/api/stats` | GET | Dashboard statistics |

## n8n Workflows

**Lead Generator** -- Runs daily at 9:00. Searches for new businesses, generates email drafts, and optionally notifies via Slack.

**Email Sender** -- Runs every 10 minutes. Picks up approved leads, sends emails with a 30-second delay between each to avoid rate limits.

Import both from `n8n/workflows/` through the n8n UI.

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## License

Private project -- not for redistribution.
