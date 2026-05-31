default:
    @just --list

build-be:
    docker build -t wandb-backend ./backend

build-fe:
    docker build -t wandb-frontend ./frontend

be-dev:
    docker compose up backend

fe-dev:
    docker compose --profile dev up frontend-dev

clean:
    docker compose down -v
