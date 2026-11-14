.PHONY: sync-tenants

sync-tenants:
	poetry run python scripts/sync_tenants.py
