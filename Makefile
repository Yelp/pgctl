.PHONY: all
all: venv test

venv: setup.py requirements.d/*.txt Makefile tox.ini
	# it's simpler to not try to make tox do this.
	rm -rf venv
	virtualenv --prompt='(pgctl)' --python=python2.7 venv
	venv/bin/pip install --upgrade pip setuptools wheel
	venv/bin/pip install --upgrade -r requirements.d/dev.txt

.PHONY: tests test
tests: test
test: .tox/py27
	tox -e py27 -- $(ARGS)

lint:
	git diff --name-only | xargs pre-commit run --files

.PHONY: spec unit
spec:
	$(eval ARGS := -k spec)
unit:
	$(eval ARGS := -k unit)

.PHONY: coverage-server
coverage-server:
	mkdir -p coverage-html
	cd coverage-html && python -m SimpleHTTPServer 0

.PHONY: docs
docs: .tox/docs
	tox -e docs

# start the tox from scratch if any of these files change
.tox/%: setup.py requirements.d/*.txt Makefile tox.ini
	rm -rf .tox/$*

.PHONY: clean
clean:
	find -name '*.pyc' -print0 | xargs -0r rm
	find -name '__pycache__' -print0 | xargs -0r rm -r
	rm -rf dist
	rm -rf docs/build
	rm -f .coverage.*
	rm -f .coverage

.PHONY: realclean
realclean: clean
	rm -rf .tox

.PHONY: release
release:
	python setup.py sdist
	twine upload --skip-existing dist/*
	fetch_python_package pgctl

# disable default implicit rules
.SUFFIXES:
%: %,v
%: RCS/%,v
%: RCS/%
%: s.%
%: SCCS/s.%
