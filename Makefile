install:
	git submodule update --init --recursive
	uv venv --python 3.12
	uv sync --extra docs --extra dev

all:
	uv run python gf180mcu/samples/all_cells.py

dev:
	uv venv --python 3.12
	uv sync --all-extras
	curl -sf https://raw.githubusercontent.com/doplaydo/pdk-ci-workflow-public/main/templates/.pre-commit-config.yaml -o .pre-commit-config.yaml
	uv run pre-commit clean
	uv run pre-commit install

tech:
	python install_tech.py

test:
	uv run pytest -s

test-ports:
	uv run pytest -s tests/test_components.py::test_optical_port_positions

test-force: install
	uv run pytest -s --update-gds-refs --force-regen

cov:
	uv run pytest --cov=gf180

update:
	pur

update-pre:
	pre-commit autoupdate --bleeding-edge

git-rm-merged:
	git branch -D `git branch --merged | grep -v \* | xargs`

release:
	git push
	git push origin --tags

build:
	rm -rf dist
	pip install build
	python -m build

jupytext:
	jupytext docs/**/*.ipynb --to py

notebooks:
	jupytext docs/**/*.py --to ipynb

nbdocs:
	rm -rf docs/intro.md
	find notebooks -maxdepth 1 -mindepth 1 -name "*.ipynb" | sort | \
		xargs -P4 -I{} uv run --extra docs jupyter nbconvert \
			--execute --to markdown --embed-images {} --output-dir docs
	uv run python docs/hooks.py docs/intro.md

sync-docs:
	uv run python -c "import re; from pathlib import Path; t=Path('CHANGELOG.md').read_text(); Path('docs/changelog.md').write_text(re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t))"
	cp README.md docs/index.md

docs-pdf: nbdocs sync-docs
	uv run python .github/write_layer_stack.py
	uv run mkdocs build -f mkdocs-pdf.yml

docs: nbdocs sync-docs
	uv run python docs/write_cells.py
	uv run python .github/write_layer_stack.py
	uv run --extra docs zensical build -f docs/zensical.toml

docs-serve: nbdocs sync-docs
	uv run python docs/write_cells.py
	uv run python .github/write_layer_stack.py
	uv run --extra docs zensical serve -f docs/zensical.toml -a localhost:8080

update-changelog:
	claude -p "remove links and make a user friendly changelog from @CHANGELOG.md to @docs/changelog.md"

.PHONY: drc drc-sample doc docs docs-pdf build update-changelog
