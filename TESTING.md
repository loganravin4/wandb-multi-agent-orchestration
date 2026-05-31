# LoopPrep — W&B Setup Verification

A step-by-step checklist to confirm the W&B integration (Weave tracing, W&B
runs, evaluations, and the MCP server) actually works end to end. Run the
phases in order; each says what to **do**, what to **expect**, and what to
**capture** if it fails. Commands are PowerShell (Windows + Docker).

---

## Phase 0 — Prerequisites (do this first)

- [ ] **`.env` is correct.** Open `.env` and confirm:
  - `WANDB_API_KEY=` your key (from https://wandb.ai/authorize)
  - `WANDB_ENTITY=` your entity — this is **not a key**, it's your W&B
    username (personal) or team/org name. Find it at the top-left team
    switcher on wandb.ai, or in your profile URL `wandb.ai/<entity>`.
  - `WANDB_PROJECT=loopprep` (or your choice)
  - `TAVILY_API_KEY=` your key (from https://app.tavily.com)
  - **No `ANTHROPIC_*` lines** (no longer used).
- [ ] **`WANDB_API_KEY` is also a Windows env var** (needed for the MCP server,
  which runs inside Claude Code, not Docker). Then restart Claude Code:
  ```powershell
  [Environment]::SetEnvironmentVariable("WANDB_API_KEY", "<your-wandb-key>", "User")
  ```

**Expected:** all four values present, Anthropic removed.

---

## Phase 1 — Build & import sanity

- [ ] **Build the image:**
  ```powershell
  docker compose build backend
  ```
- [ ] **Confirm the app imports** (catches broken imports before runtime):
  ```powershell
  docker compose run --rm backend python -c "import app.main; print('import OK')"
  ```

**Expected:** build succeeds; prints `import OK`.
**If it fails:** capture the full traceback — an `ImportError`/`NameError` here
means a code wiring issue, not a W&B problem.

---

## Phase 2 — Services up & healthy

- [ ] **Start everything:**
  ```powershell
  docker compose up --build
  ```
- [ ] **Backend liveness/readiness:**
  ```powershell
  Invoke-RestMethod http://localhost:8000/api/health
  Invoke-RestMethod http://localhost:8000/api/ready
  ```
- [ ] **Frontend loads:** open http://localhost:5173
- [ ] **API docs load:** open http://localhost:8000/docs

**Expected:** health/ready return OK; pages load.
**If it fails:** the backend should *refuse to start* if a required env var is
missing (by design) — check the `docker compose up` logs for
`Missing required environment variables: ...`.

---

## Phase 3 — Weave tracing (the core of Steps 1–2)

- [ ] **Create a session** (runs the research → format agents):
  ```powershell
  $body = @{
    job_description = "Senior Backend Engineer building high-throughput payment APIs in Python. Owns reliability and on-call."
    company = "Stripe"
    role = "Senior Backend Engineer"
    seniority = "senior"
  } | ConvertTo-Json

  Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/sessions `
    -ContentType "application/json" -Body $body
  ```

**Expected:** HTTP 200 with a `session_id`, `phase`, and a `questions` array
(3 questions with `type`/`text`/`difficulty`).

- [ ] **Find the Weave trace.** In the `docker compose up` logs, look for a line
  with a Weave URL (`https://wandb.ai/<entity>/loopprep/r/...`), or open
  `https://wandb.ai/<entity>/loopprep/weave/traces` directly.

**Expected in Weave:** a trace tree showing `research_node` and `format_node`,
each with a **nested LLM call** (the W&B Inference chat completion via
`ChatOpenAI`), plus a `search` (Tavily) span under research. Inputs/outputs,
latency, and model ID should be visible.

**Capture if it fails:** the API response, and whether the trace appears at all
(auth issue) vs. appears but is missing nested LLM spans (patching issue).

---

## Phase 4 — W&B run & session metrics (W&B Core)

- [ ] In the same project, open the **Runs/Workspace** view:
  `https://wandb.ai/<entity>/loopprep`

**Expected:** a run named `session-xxxxxxxx` (matching your `session_id`), with
config (`session_id`, `job_description_preview`) and any logged metrics /
the `question-queue-*` artifact.

---

## Phase 5 — Evaluations (Step 4)

- [ ] **Run the eval harness:**
  ```powershell
  docker compose run --rm backend python -m app.evals.run_eval
  ```

**Expected (console):** one line per sample, e.g.
`eval-backend-001: question_count_ok=1.00, schema_validity=1.00, relevance=0.85`,
then a `Summary:` line with the three `_avg` metrics.

- [ ] **Confirm in Weave:** open the project's **Evals** tab:
  `https://wandb.ai/<entity>/loopprep/weave/evaluations`

**Expected:** an evaluation for model `format-agent` / dataset `jd-samples-v1`
with per-prediction scores and the aggregate summary.

**Capture if it fails:** the console output (a low `schema_validity` means the
model isn't returning clean JSON; a crash means a logging/API issue).

---

## Phase 6 — W&B MCP server (Step 3)

- [ ] **Start a fresh Claude Code session** in this project. When prompted,
  **approve** the project-scoped `wandb` MCP server.
- [ ] **Confirm it's connected:**
  ```
  /mcp
  ```
  **Expected:** `wandb` listed as connected.
- [ ] **Hand it back to me.** Tell me it's connected and I'll verify by calling
  a W&B MCP tool — e.g. list your projects and count the Weave traces from
  Phase 3 / summarize the eval from Phase 5 — to prove the round-trip works.

**Capture if it fails:** whether `/mcp` shows `wandb` at all (config issue) vs.
shows it failing to connect (the `${WANDB_API_KEY}` env var from Phase 0 isn't
visible to Claude Code — re-check it and fully restart).

---

## Report-back template

> - Phase 1 import: ✅ / ❌ (paste error)
> - Phase 2 health: ✅ / ❌
> - Phase 3 trace tree visible w/ nested LLM spans: ✅ / ❌
> - Phase 4 session run visible: ✅ / ❌
> - Phase 5 eval in Evals tab: ✅ / ❌ (paste Summary line)
> - Phase 6 MCP connected: ✅ / ❌
