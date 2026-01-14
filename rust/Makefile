.PHONY: help build test check clippy fmt run dev watch clean bench

help:
	@echo "Rust Development Commands:"
	@echo "  make build      - Build release binary"
	@echo "  make test       - Run tests"
	@echo "  make check      - Run all checks (clippy + fmt + test)"
	@echo "  make clippy     - Run clippy linter"
	@echo "  make fmt        - Format code"
	@echo "  make run        - Run server binary"
	@echo "  make dev        - Run with hot reload"
	@echo "  make watch      - Watch and test on changes"
	@echo "  make bench      - Run benchmarks"
	@echo "  make clean      - Clean build artifacts"

build:
	cargo build --release

test:
	cargo test

check: clippy fmt test
	@echo "All checks passed"

clippy:
	cargo clippy -- -D warnings

fmt:
	cargo fmt --all -- --check

fmt-fix:
	cargo fmt --all

run:
	cargo run --bin server

dev:
	cargo watch -x 'run --bin server'

watch:
	cargo watch -x test

bench:
	cargo bench

clean:
	cargo clean
