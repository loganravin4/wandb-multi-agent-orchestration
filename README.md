  # LoopPrep — Multi-Agent Interview Coach

  Paste a job description. Speak your answers out loud. Get a calibrated mock interview built around how that company actually interviews — with per-question content and delivery
  scoring, traced live in W&B Weave.

  Built at AGI House x W&B Build Day, May 31 2026.

  ## Tech stack
  
  | Layer | Tool |
  |---|---|
  | Agent orchestration | LangGraph |
  | Backend API | FastAPI + Uvicorn |
  | Inference client | openai SDK (W&B Serverless Inference endpoint) |
  | LLM | W&B Serverless Inference — see agent model breakdown below |
  | Transcription | Whisper local (`openai-whisper`, base model, CPU) |
  | LLM tracing + eval | W&B Weave |
  | Session metrics | W&B Core |
  | Research | Tavily |
  | Frontend | React + Vite (Node 20) |
  | Containerization | Docker + Docker Compose |
  | Backend runtime | Python 3.11 |

  ## Agents
  
  | Agent | Model | Job |
  |---|---|---|
  | JD Parser | `meta-llama/Llama-3.1-8B-Instruct` | Extracts technical + behavioral signals from the JD |
  | Research Agent | `meta-llama/Llama-3.3-70B-Instruct` | Looks up how the target company actually interviews |
  | Format Agent | `meta-llama/Llama-3.3-70B-Instruct` | Builds the ordered question queue |
  | Interviewer Agent | `meta-llama/Llama-3.3-70B-Instruct` | Runs the session, scores content per answer |
  | Delivery Agent | `meta-llama/Llama-3.1-8B-Instruct` | Scores communication from Whisper transcript |
  | Report Agent | `deepseek-ai/DeepSeek-V3-0324` | Generates final session debrief |

  ## Project layout

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

  ## Quick start (Docker — Mac + Windows)
  
  1. Copy env template and fill in API keys:
     ```bash
     cp .env.example .env

  2. Start backend + production frontend:
  docker compose up --build
    - Frontend: http://localhost:5173
    - Backend API: http://localhost:8000
    - API docs: http://localhost:8000/docs
  3. Dev mode with Vite hot reload:
  docker compose --profile dev up --build

  ## W&B MCP server (Claude Code)

  This repo ships a pre-configured W&B MCP server so coding agents (and you) can
  query Weave traces, W&B runs, and evals directly from Claude Code. It is
  committed and auto-approved — no per-developer approval prompt:

  - `.mcp.json` — defines the hosted `wandb` server, authenticated with
    `${WANDB_API_KEY}` (no secret committed).
  - `.claude/settings.json` — auto-trusts it via `enabledMcpjsonServers: ["wandb"]`.

  Each developer only needs their own W&B API key in Claude Code's environment.
  The easiest way is a personal, gitignored `.claude/settings.local.json`:

  ```json
  { "env": { "WANDB_API_KEY": "your-wandb-key" } }
  ```

  (Alternatively, set `WANDB_API_KEY` as an OS environment variable.) Then open
  Claude Code in the repo root and run `/mcp` — `wandb` should show **connected**.

  Local development (without Docker)

  Backend
  
  cd backend
  python -m venv .venv
  source .venv/bin/activate        # Mac/Linux
  # .venv\Scripts\Activate.ps1    # Windows PowerShell
  pip install -r requirements.txt
  cp ../.env.example .env
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  Frontend

  cd frontend
  npm install
  npm run dev
  Vite proxies /api → http://127.0.0.1:8000 (see vite.config.ts).

  API overview

  | Method | Path | Description |
  |--------|------|-------------|
  | `GET` | `/api/health` | Liveness check |
  | `GET` | `/api/ready` | Readiness check |
  | `POST` | `/api/sessions` | Create session (runs ingest pipeline) |
  | `GET` | `/api/sessions/{id}` | Get session state |
  | `POST` | `/api/sessions/{id}/transcribe` | Upload audio → Whisper transcript |
  | `POST` | `/api/sessions/{id}/hint` | Trigger Socratic hint path |
  | `GET` | `/api/sessions/{id}/report` | Get final report, close W&B run |

  
  Agent graph

  START → jd_parser → [research ‖ format] → interviewer_loop → report → END

  Interviewer loop: present question → record audio → transcribe → score content + delivery → advance queue.

  Environment variables
  
  See .env.example. All four required before the backend will start:

  - WANDB_API_KEY
  - WANDB_ENTITY
  - WANDB_PROJECT
  - TAVILY_API_KEY
  
  Cross-platform notes

  - Paths: temp audio files use tempfile (not hard-coded /tmp).
  - Docker volumes: named volume for node_modules avoids Mac/Windows bind-mount perf issues in dev profile.
  - Line endings: repo uses LF; Git on Windows should use core.autocrlf=true (default).
