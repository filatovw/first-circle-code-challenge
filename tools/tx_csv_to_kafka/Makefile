.DEFAULT_GOAL := help
APP := ingestion 

## install - install core dependencies
.PHONY: install
install:
	uv sync

## install/test - install testing/linting dependencies
.PHONY: install/test
install/test:
	uv sync --group test

## install/dev - install testing and debugging tools
.PHONY: install/dev
install/dev:
	uv sync --group test --group dev

## lint - execute linter
.PHONY: lint
lint:
	uv run ruff check

## lint/fix - execute linter and apply propsed fixes
.PHONY: lint/fix
lint/fix:
	uv run ruff check --fix

## fmt - apply formatter
fmt:
	uv run ruff format

## test - run tests
.PHONY: test
test:
	uv run pytest tests/

## typecheck - check typing annotations
.PHONY: typecheck
typecheck:
	uv run mypy .

## app/help - show the application help
.PHONY: app/help
app/help:
	uv run ${APP} -h

## clean - delete trash files
.PHONY: clean
clean:
	@echo "Deleting unnecessary files"
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info
	@rm -rf *.pyc
	@rm -rf .*_cache
	@rm -rf __pycache__/
	@find . -name '*.pyc' -delete
	@find . -name '__pycache__' -delete


## -
## help - this message
.PHONY: help
help: Makefile
	@echo "Application: ${APP}\n"
	@echo "Run command:\n  make <target>\n"
	@grep -E -h '^## .*' $(MAKEFILE_LIST) | sed -n 's/^##//p'  | column -t -s '-' |  sed -e 's/^/ /'
