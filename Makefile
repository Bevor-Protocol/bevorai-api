dev:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

init-db:
	poetry run aerich init-db

init-config:
	poetry run aerich init -t app.db.config.TORTOISE_ORM --location app/db/migrations