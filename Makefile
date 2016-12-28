export PATH := $(PWD)/bin:$(PWD)/venv/bin:$(PATH)
export PYTHON?=python2.7
export REQUIREMENTS?=requirements.d/dev.txt

.PHONY: all
all: test

venv: setup.py requirements.d/*.txt Makefile tox.ini
	# it's simpler to not try to make tox do this.
	rm -rf venv
	virtualenv --prompt='(pgctl)' --python=$(PYTHON) venv
	pip install --upgrade pip setuptools wheel
	pip install --upgrade -r $(REQUIREMENTS)

.PHONY: test tests
test tests: venv
	./test $(ARGS)

.PHONY: install-hooks
install-hooks: venv
	pre-commit install -f --install-hooks

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
	git clean -fdXf

.PHONY: clean-pyc
clean-pyc:
	find -name '*.pyc' | xargs rm

.PHONY: release
release:
	python setup.py sdist bdist_wheel
	twine upload --skip-existing dist/*
	fetch-python-package pgctl

# standard Makefile housekeeping
.SUFFIXES:
MAKEFLAGS += --no-builtin-rules
