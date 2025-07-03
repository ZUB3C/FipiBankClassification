lint:
    uv run ruff check --fix
    uv run ruff format

typing:
    uv run basedpyright

migration message:
	uv run alembic revision \
	  --autogenerate \
	  --rev-id `python migrations/_get_next_revision_id.py` \
	  --message "{{ message }}"

command message:
    just migration message="{{message}}"

migrate:
	uv run alembic upgrade head
