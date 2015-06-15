.PHONY: all
all: venv test

.PHONY: venv
venv:  .tox/pgctl .tox/venv
	# it's simpler to not try to make tox do this.
	virtualenv --python=python2.7 .tox/pgctl
	.tox/pgctl/bin/pip install --upgrade -r requirements.d/dev.txt
	ln -sf pgctl .tox/venv

.PHONY: tests test
tests: test
test: .tox/test
	tox -- "$(ARGS)"

.PHONY: docs
docs: .tox/docs
	tox -e docs

# start the tox from scratch if any of these files change
.tox/%: setup.py requirements.d/*.txt Makefile tox.ini
	rm -rf .tox/$*

.PHONY: clean
clean:
	find -name '*.pyc' | xargs -r rm
	find -name '__pycache__' | xargs -r rm -r
	rm -rf .tox
