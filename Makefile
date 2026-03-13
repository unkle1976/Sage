.PHONY: dev test migrate seed worker up down

dev:
	cd backend && source .venv/bin/activate && python run.py

worker:
	cd backend && source .venv/bin/activate && arq app.tasks.worker.WorkerSettings

test:
	cd backend && source .venv/bin/activate && pytest tests/ -v --tb=short

migrate:
	cd backend && source .venv/bin/activate && alembic upgrade head

seed:
	cd backend && source .venv/bin/activate && python -m app.data.seed_plants

up:
	docker compose up -d

down:
	docker compose down
