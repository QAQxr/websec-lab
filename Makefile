.PHONY: up down reset test verify

up:
	docker compose up -d --build

down:
	docker compose down --remove-orphans

reset:
	./scripts/reset.sh

test:
	docker compose --profile test run --rm test-runner

verify:
	./scripts/verify_phase21.sh
