.POSIX:

project_dir := .

lint:
	@ruff format --check --diff $(project_dir)
	@ruff check $(project_dir)
	@mypy --strict $(project_dir)

format:
	@ruff format $(project_dir)
	@ruff check --fix $(project_dir)

.PHONY: lint, format
