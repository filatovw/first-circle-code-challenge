APP := service
.DEFAULT_GOAL := help

## sql-lint: lint migrations and seeds with SQLFluff
sql-lint:
	sqlfluff lint ./migrations --dialect postgres

## sql-fix: apply auto-fixes to migrations and seeds with SQLFluff
sql-fix:
	sqlfluff fix ./migrations --dialect postgres


## up: spin-up the infra except for the application
up:
	docker compose config --services | xargs docker compose up

## down: shutdown the infra
down:
	docker compose down

## clean: drop created resources and artifacts
clean:
	${MAKE} down
	rm -rf volumes/db

## :
## help - this message
.PHONY: help
help: Makefile
	@echo "Application: ${APP}\n"
	@echo "Run command:\n  make <target>\n"
	@grep -E -h '^## .*' $(MAKEFILE_LIST) | sed -n 's/^##//p'  | column -t -s ':' |  sed -e 's/^/ /'
