server:
	./scripts/connect.sh

log:
	@echo "Usage: make log GMA_HOST=<ip>"
	telnet $(GMA_HOST) 30001

test:
	uv run pytest -v

install-hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	@echo "Git hooks installed. Pre-commit will auto-update the RAG index."
