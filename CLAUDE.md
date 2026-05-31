# LoopPrep — CLAUDE.md

Multi-agent mock interview coach built at AGI House x W&B Build Day, May 31 2026.

---

## Hackathon Context

**Event:** Multi-Agent Orchestration Build Day — AGI House x W&B x TNT x SundAI Club x E14
**Venue:** The Engine, 750 Main St, Cambridge, MA
**Submissions:** Draft due 7pm, final due 8pm, judging begins 8pm

**Prizes:**
- 1st: Most Sophisticated Harness — Unitree G2 Pro Robot Dog + $2,000 cash
- 2nd: $2,000 cash + Hugging Face Reachy Mini (per team member)
- 3rd: $1,000 cash + TRMNL e-ink frame
- Best Use of Weave: $1,000 cash

**Judging criteria (in order of importance):**
1. Agent Orchestration — multiple agents meaningfully working together
2. Utility — solves a real problem
3. Technical Execution — does it work, are architecture decisions sound
4. Creativity — novel approach or problem
5. Sponsor Usage — meaningful use of W&B Weave and W&B Core

**Eligibility:** Code must be in a public GitHub repo. Project must be built entirely at the event.

---

## What LoopPrep Does

User pastes a job description and speaks answers out loud. The system:

1. Parses the JD to extract technical requirements and behavioral themes
2. Researches how that specific company interviews using Tavily web search
3. Builds a calibrated question queue (type mix, difficulty, sequence) based on role and company
4. Runs a live interview loop — user records audio, Whisper transcribes it, agents score content and delivery per question
5. Generates a full session debrief with strengths, weaknesses, and three concrete next steps

Every agent call is traced individually in W&B Weave. Per-question scores are logged to a W&B session dashboard. Two dashboards, two stories, one platform.

**Why this is differentiated:** No existing tool combines audio-native answering, JD-specific question generation, delivery scoring from live transcripts, and company-specific research. Each of those exists in isolation somewhere. Together they don't.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Agent orchestration | LangGraph |
| Backend API | FastAPI + Uvicorn |
| Inference client | openai SDK pointed at W&B Serverless Inference endpoint |
| LLM | W&B Serverless Inference models (see agent breakdown below) |
| Transcription | Whisper local (openai-whisper, base model, CPU) |
| LLM tracing + structured eval | W&B Weave |
| Session metrics + run tracking | W&B Core |
| Research | Tavily |
| Frontend | React + Vite (Node 20) |
| Containerization | Docker + Docker Compose |
| Backend runtime | Python 3.11 |

---

## Inference Setup (Critical)

All LLM calls go through the W&B Serverless Inference endpoint, not Anthropic or OpenAI directly. The `openai` Python SDK is used as the client with a custom base URL.

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.inference.wandb.ai/v1",
    api_key=os.environ["WANDB_API_KEY"],
    project=f"{os.environ['WANDB_ENTITY']}/{os.environ['WANDB_PROJECT']}",
)
```

**Available models:**
- `meta-llama/Llama-3.1-8B-Instruct` — fast, lightweight tasks
- `meta-llama/Llama-3.3-70B-Instruct` — complex reasoning, conversation
- `deepseek-ai/DeepSeek-V3-0324` — strong synthesis and reasoning
- `deepseek-ai/DeepSeek-R1-0528` — optimized for coding and precise reasoning
- `meta-llama/Llama-4-Scout-17B-16E-Instruct` — multimodal (text + vision)
- `microsoft/Phi-4-mini-instruct` — very fast, minimal tasks

**Concurrency limit:** W&B enforces per-user rate limits. The ingest phase fires Research Agent and JD Parser in parallel — keep the fan-out to those two only. Do not add more parallel calls at the same stage.

---

## Agents (6 Total)

### 1. JD Parser
**Model:** `meta-llama/Llama-3.1-8B-Instruct`
**Job:** Extracts all signals from the job description in a single structured pass.
- Technical pass: required stack, seniority level, domain focus
- Behavioral pass: values language, ownership signals, leadership expectations

**Output:** Pydantic model with structured fields
**Weave:** `@weave.op()` — logs raw JD input and structured extraction output
**W&B:** Session config logged at start

### 2. Research Agent
**Model:** `meta-llama/Llama-3.3-70B-Instruct`
**Job:** Web searches how that specific company actually interviews. Surfaces interview format first (coding-heavy, system design, take-home, pair programming), then common question topics within that format. Uses Tavily for search.

**Output:** Structured format report with interview style and common topics
**Weave:** `@weave.op()` — logs search queries, raw results, structured output
**W&B:** `wandb.log({"interview_format": ..., "common_topics": ...})` at session start

### 3. Format Agent
**Model:** `meta-llama/Llama-3.3-70B-Instruct`
**Job:** Takes JD Parser + Research Agent outputs and builds the ordered question queue. Decides question count, type mix (coding vs behavioral), difficulty distribution, and sequence. A Google L3 JD produces a different queue than a startup senior engineer JD.

**Output:** Ordered list of Question objects published as `weave.Dataset`
**Weave:** `@weave.op()` + `weave.Dataset` — question queue as traceable rows
**W&B:** `wandb.Artifact` — versions the question queue for reproducibility

### 4. Interviewer Agent
**Model:** `meta-llama/Llama-3.3-70B-Instruct`
**Job:** Presents one question at a time. Evaluates content inline after each answer — coding answers on correctness, approach, and edge cases; behavioral answers on STAR completeness. Manages session state, advances the queue, knows when the session is done. Also handles the Socratic hint path when the candidate requests help (asks guiding questions without revealing the answer).

**Weave:** `@weave.op()` on question presentation AND content evaluation separately — both individually traceable
**W&B:** `wandb.log({"question_index": ..., "question_type": ..., "content_score": ...})` per turn

### 5. Delivery Agent
**Model:** `meta-llama/Llama-3.1-8B-Instruct`
**Job:** Runs on the Whisper transcript after every answer regardless of question type. Computes filler rate and WPM directly from transcript and duration, then passes to the model for qualitative scoring on structure, clarity, and pacing.

**Output:** Structured delivery scores with WPM, filler rate, and qualitative breakdown
**Weave:** `@weave.op()` — logs transcript, computed signals (WPM, filler rate), structured scores
**W&B:** `wandb.log({"delivery_score": ..., "wpm": ..., "filler_rate": ...})` per turn

### 6. Report Agent
**Model:** `deepseek-ai/DeepSeek-V3-0324`
**Job:** Runs once after the queue is empty. Takes all content + delivery scores across the session, identifies the weakest area, writes a structured debrief: summary, strengths, areas to improve, three concrete next steps.

**Weave:** Logs as `weave.Evaluation` object — full session summary linking all question traces. This is the money shot in the Weave dashboard.
**W&B:** `wandb.log({"final_content_score": ..., "final_delivery_score": ..., "final_overall": ...})` closes the run

---

## Agent Orchestration Flow (LangGraph)

```
START
  └── jd_parser
        └── [research_agent ‖ format_agent]  ← parallel fan-out
              └── interviewer_loop
                    ├── present_question
                    ├── transcribe_audio (Whisper)
                    ├── [content_eval ‖ delivery_eval]  ← parallel per turn
                    ├── log_scores
                    └── (loop until queue empty)
                          └── report_agent
                                └── END
```

Every agent is a LangGraph node. Every transition is a LangGraph edge. LangGraph owns the state machine — it does not do tracing, evaluation, or metric logging.

---

## W&B Weave Integration

Weave owns LLM observability and structured evaluation. Auto-patches the OpenAI client on `weave.init()` so every LLM call is individually traced without extra code. `@weave.op()` on each agent function makes the orchestration layer visible on top of LLM calls.

| Agent | Weave | W&B Core |
|---|---|---|
| JD Parser | `@weave.op()` | session config |
| Research Agent | `@weave.op()` | log format + topics |
| Format Agent | `@weave.op()` + `weave.Dataset` | `wandb.Artifact` question queue |
| Interviewer Agent | `@weave.op()` x2 (present + evaluate) | log content score per turn |
| Delivery Agent | `@weave.op()` | log delivery score, WPM, filler rate per turn |
| Report Agent | `weave.Evaluation` | log final scores, `finish()` run |

**Initialization pattern (observability.py):**
```python
import weave
import wandb

def init_observability(session_id: str):
    weave.init(f"{os.environ['WANDB_ENTITY']}/{os.environ['WANDB_PROJECT']}")
    wandb.init(
        project=os.environ["WANDB_PROJECT"],
        entity=os.environ["WANDB_ENTITY"],
        name=session_id,
        config={"session_id": session_id}
    )
```

**Demo separation:**
- Weave tab: agent graph, individual call traces, per-question structured scores, weave.Dataset, weave.Evaluation
- W&B tab: session run dashboard, per-question metric logs, score trajectory over session

---

## Project Structure

```
wandb-multi-agent-orchestration/
├── docker-compose.yml
├── .env.example
├── README.md
├── CLAUDE.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI app, Whisper transcription, session store
│       ├── graph.py         # LangGraph state machine, all nodes and edges
│       ├── agents.py        # All 6 agents with @weave.op()
│       ├── state.py         # SessionState TypedDict, Question, QuestionResult
│       ├── observability.py # weave.init() + wandb.init() + log helpers
│       ├── config.py        # pydantic-settings, env var loading
│       ├── agents/          # individual agent modules if split out
│       ├── routers/         # FastAPI route handlers
│       └── services/        # LLM client, Whisper client, Tavily client
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── App.tsx
        ├── api/             # typed fetch client
        └── components/
            ├── JDInput.tsx  # JD paste + start session
            ├── Interview.tsx # MediaRecorder, hint button, per-Q feedback
            └── Report.tsx   # Final session report display
```

---

## Backend Libraries (requirements.txt)

```
openai
weave
wandb
langgraph
langchain-core
pydantic
fastapi
uvicorn
tavily-python
openai-whisper
python-multipart
```

---

## State Schema (state.py)

```python
class Question(TypedDict):
    index: int
    type: str  # "coding" | "behavioral" | "system_design"
    text: str
    difficulty: str

class QuestionResult(TypedDict):
    question: Question
    transcript: str
    content_score: float
    delivery_score: float
    wpm: float
    filler_rate: float
    hint_used: bool

class SessionState(TypedDict):
    session_id: str
    jd_text: str
    jd_parsed: dict
    research: dict
    question_queue: list[Question]
    current_index: int
    results: list[QuestionResult]
    status: str  # "ingesting" | "interviewing" | "complete"
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/ready` | Readiness check |
| POST | `/api/sessions` | Create session — runs ingest pipeline, returns session ID + first question |
| GET | `/api/sessions/{id}` | Get session state |
| POST | `/api/sessions/{id}/transcribe` | Upload audio blob → Whisper transcript |
| POST | `/api/sessions/{id}/hint` | Trigger Socratic hint path in Interviewer Agent |
| GET | `/api/sessions/{id}/report` | Get Report Agent output, close W&B run |

---

## Environment Variables

```
WANDB_API_KEY=        # covers both W&B Serverless Inference and observability
WANDB_ENTITY=         # W&B team/username
WANDB_PROJECT=loopprep
TAVILY_API_KEY=       # Research Agent web search
```

No Anthropic API key. All inference goes through W&B Serverless Inference using WANDB_API_KEY.

---

## Docker Setup

```
docker compose up --build

Frontend: http://localhost:5173
Backend:  http://localhost:8000
API docs: http://localhost:8000/docs

Dev mode (hot reload): docker compose --profile dev up --build
```

Backend: Python 3.11-slim, ffmpeg installed at build time (Whisper dependency), Whisper base model pre-downloaded into a named volume so it doesn't block the first request.

Frontend: Node 20-slim, Vite dev server with `--host 0.0.0.0`, hot reload mounted.

---

## Frontend Audio Flow

MediaRecorder API (native browser, no library needed) captures audio in React. On answer submission, the audio blob is POST'd to `/api/sessions/{id}/transcribe` as multipart form data. FastAPI receives it, runs Whisper locally, returns the transcript. The transcript then goes to Interviewer Agent (content eval) and Delivery Agent (delivery eval) in parallel.

---

## MVP Scope

Must work end to end before any stretch goals:

- JD input in React
- Ingest pipeline: JD Parser → [Research + Format in parallel] → question queue
- Audio recording via MediaRecorder in React
- Whisper transcription on answer submission
- Interviewer Agent content evaluation per question
- Delivery Agent scoring every transcript
- Question-by-question loop with next question after each answer
- Hint button triggering Socratic path
- Session ends, Report Agent runs, report displayed
- Weave dashboard: all 6 agent traces + weave.Dataset + weave.Evaluation
- W&B dashboard: session run with per-turn metric logs

## Stretch Goals (only if MVP solid by 5pm)

- Real-time filler word counter visible during recording
- WebSocket streaming agent status to React during ingest
- Score trend chart across multiple sessions in W&B
- Difficulty adaptation mid-session based on content scores

---

## Demo Script (3 minutes)

1. Paste a real Google L4 SWE JD on screen
2. Flip to Weave — show JD Parser, Research, Format traces firing, question queue in weave.Dataset
3. Return to app — first coding question appears
4. Hit record, speak answer, submit
5. Flip to Weave — show Interviewer Agent content eval trace + Delivery Agent trace side by side
6. Show Content score + Delivery score in the UI
7. Hit hint — show Socratic path trace in Weave
8. Complete session, show Report on screen
9. Flip to W&B — show session run, per-turn score chart, final aggregate
10. Flip back to Weave — show weave.Evaluation full session summary

Two dashboards. Two stories. One platform.

---

## Judging Alignment

| Criterion | How we hit it |
|---|---|
| Agent Orchestration | 6 agents, LangGraph state machine, parallel fan-out in ingest + parallel content/delivery eval per turn |
| Utility | Audio-native + JD-specific + delivery scoring — this combination doesn't exist in any tool |
| Technical Execution | LangGraph + FastAPI + React + Whisper + Docker, cross-platform |
| Creativity | Delivery Agent scoring spoken communication on every answer is novel |
| Sponsor Usage | Weave: @weave.op() x6, weave.Dataset, weave.Evaluation / W&B: wandb.init(), wandb.log() per turn, wandb.Artifact |
