.PHONY: sync-tenants test

sync-tenants:
	poetry run python scripts/sync_tenants.py

test:
	uv run --no-project --python 3.13 --with-requirements requirements.txt pytest -q
