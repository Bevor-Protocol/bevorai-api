.PHONY: dev

dev:
	poetry run fastapi dev app/main.py --host localhost --port 8000

run:
	poetry run fastapi run app/main.py
