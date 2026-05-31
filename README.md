# wandb-multi-agent-orchestration

Multi-agent interview prep powered by LangGraph, with W&B Weave tracing and session metrics.

## Tech stack

| Layer | Tool |
|---|---|
| Agent orchestration | LangGraph |
| Backend API | FastAPI + Uvicorn |
| LLM | Claude `claude-sonnet-4-20250514` (Anthropic) |
| Transcription | Whisper local (`openai-whisper`, base model, CPU) |
| LLM tracing + eval | W&B Weave |
| Session metrics | W&B Core |
| Research | Tavily |
| Frontend | React + Vite (Node 20) |
| Containerization | Docker + Docker Compose |
| Backend runtime | Python 3.11 |

## Project layout

```
backend/
  app/
    agents/       # LangGraph graph + node implementations
    routers/      # FastAPI routes
    services/     # LLM, Whisper, Tavily clients
    config.py     # pydantic-settings
    main.py       # FastAPI entrypoint
    observability.py
    state.py
  Dockerfile
  requirements.txt
frontend/
  src/
    api/          # typed fetch client
    App.tsx
  Dockerfile
docker-compose.yml
.env.example
```

## Quick start (Docker — Mac + Windows)

1. Copy env template and fill in API keys:

   ```bash
   cp .env.example .env
   ```

2. Start backend + production frontend:

   ```bash
   docker compose up --build
   ```

   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs

3. **Dev mode** with Vite hot reload:

   ```bash
   docker compose --profile dev up --build
   ```

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv

# Mac / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp ../.env.example .env   # edit with your keys

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` → `http://127.0.0.1:8000` (see `vite.config.ts`).

## API overview

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/ready` | Readiness check |
| POST | `/api/sessions` | Create session (runs research → format agents) |
| GET | `/api/sessions/{id}` | Get session state |
| POST | `/api/sessions/{id}/transcribe` | Upload audio → Whisper transcript |

## Agent graph (current)

```
START → research (Tavily + Claude) → format (question queue) → END
```

Interview loop, scoring, and report nodes are stubbed for you to build next.

## Cross-platform notes

- **Paths**: temp audio files use `tempfile` (not hard-coded `/tmp`).
- **Docker volumes**: named volume for `node_modules` avoids Mac/Windows bind-mount perf issues in dev profile.
- **Line endings**: repo uses LF; Git on Windows should use `core.autocrlf=true` (default).

## Environment variables

See [`.env.example`](.env.example). Required for full functionality:

- `ANTHROPIC_API_KEY`
- `TAVILY_API_KEY`
- `WANDB_API_KEY`
