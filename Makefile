.PHONY: all
all: venv test

.PHONY: venv
venv:
	tox -e venv

.PHONY: tests test
test: install-hooks
	tox -e py27 -- $(ARGS)

.PHONY: install-hooks
install-hooks: venv
	venv/bin/pre-commit install -f --install-hooks

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
docs:
	tox -e docs

.PHONY: clean
clean:
	find -name '*.pyc' -print0 | xargs -0r rm
	find -name '__pycache__' -print0 | xargs -0r rm -r
	rm -rf dist
	rm -rf docs/build
	rm -f .coverage.*
	rm -f .coverage
	rm -rf .tox

.PHONY: release
release:
	python setup.py sdist bdist_wheel
	twine upload --skip-existing dist/*
	fetch-python-package pgctl

# disable default implicit rules
.SUFFIXES:
%: %,v
%: RCS/%,v
%: RCS/%
%: s.%
%: SCCS/s.%
