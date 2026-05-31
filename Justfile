set dotenv-load

# List available recipes
default:
    @just --list

# ── Docker Compose (full stack) ───────────────────────────────────────────────

# Build and start all services
up:
    docker compose up --build

# Start all services (no rebuild)
start:
    docker compose up

# Start with Vite HMR dev frontend instead of nginx
dev:
    docker compose --profile dev up --build

# Stop all services
down:
    docker compose down

# Stop and remove volumes
clean:
    docker compose down -v

# Tail logs for all services
logs:
    docker compose logs -f

# ── Backend ───────────────────────────────────────────────────────────────────

# Build the backend image
build-backend:
    docker build -t wandb-backend ./backend

# Run the backend container standalone
run-backend:
    docker run --rm -p 8000:8000 --env-file .env wandb-backend

# Tail backend logs (compose)
logs-backend:
    docker compose logs -f backend

# Open a shell in the running backend container
shell-backend:
    docker compose exec backend sh

# ── Frontend ──────────────────────────────────────────────────────────────────

# Build the frontend image
build-frontend:
    docker build -t wandb-frontend ./frontend

# Run the frontend container standalone
run-frontend:
    docker run --rm -p 5173:80 wandb-frontend

# Tail frontend logs (compose)
logs-frontend:
    docker compose logs -f frontend

# Open a shell in the running frontend container
shell-frontend:
    docker compose exec frontend sh
