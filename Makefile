.PHONY: install dev test cov up down run seed bench-search bench-topk bench-cache load-test

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

dev:
	cp -n .env.example .env || true

test:
	pytest tests/ -v

cov:
	pytest tests/ --cov=app --cov-report=term-missing

up:
	docker compose up --build -d

down:
	docker compose down

run:
	uvicorn app.main:app --reload

seed:
	python scripts/generate_sample_data.py
	python scripts/seed_db.py --reset

bench-search:
	python benchmarks/bench_search_vs_linear.py

bench-topk:
	python benchmarks/bench_topk.py

bench-cache:
	python benchmarks/bench_cache.py --host http://localhost:8000

load-test:
	locust -f benchmarks/locustfile.py --headless -u 50 -r 10 -t 30s --host http://localhost:8000 --csv benchmarks/results/locust
