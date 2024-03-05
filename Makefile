install:
	pip install -e .[dev,docs]

dev:
	pip install -e .[dev,docs]
	pre-commit install

tech:
	python install_tech.py

test:
	pytest -s

cov:
	pytest --cov=gf180

mypy:
	mypy . --ignore-missing-imports

pylint:
	pylint gf180

ruff:
	ruff --fix gf180/*.py

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
	jb build docs

.PHONY: drc doc docs
