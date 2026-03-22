# FollowTheFootPrints – dev shortcuts
# Uses uv; run `uv sync --dev` first if needed

.PHONY: test run setup lint backtest

test:
	uv run pytest

run:
	uv run ftf

backtest:
	uv run python experiments/demand_zone_backtest.py

setup:
	./setup.sh

# Install dev deps (for CI or fresh clone)
sync:
	uv sync --dev
