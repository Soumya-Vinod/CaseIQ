.PHONY: install run worker migrate revision test up down seed
install:        ; pip install -r requirements.txt
run:            ; uvicorn app.main:app --reload
worker:         ; arq app.tasks.worker.WorkerSettings
migrate:        ; alembic upgrade head
revision:       ; alembic revision --autogenerate -m "$(m)"
test:           ; pytest -q
up:             ; docker compose up --build
down:           ; docker compose down -v
seed:           ; python -m scripts.ingest_sections --all
