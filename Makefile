install:
	uv sync --extra docs --extra dev

dev:
	uv sync --all-extras
	uv pip install -e .
	uv run pre-commit install

tech:
	python install_tech.py

test:
	uv run pytest -s

test-force:
	uv run pytest -s --force-regen

cov:
	uv run pytest --cov=gf180


git-rm-merged:
	git branch -D `git branch --merged | grep -v \* | xargs`

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


docs:
	uv run python docs/write_cells.py
	uv run jb build docs

.PHONY: drc doc docs
