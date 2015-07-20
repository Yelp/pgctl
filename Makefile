REBUILD_FLAG =

.PHONY: all
all: venv test

.PHONY: venv
venv:  .tox/venv
.tox/venv: .tox/venv.rebuild
	# it's simpler to not try to make tox do this.
	mkdir -p .tox
	rm -rf .tox/pgctl
	virtualenv .tox/pgctl --python=python2.7
	.tox/pgctl/bin/pip install --upgrade pip
	.tox/pgctl/bin/pip install --upgrade -r requirements.d/dev.txt
	ln -sf pgctl .tox/venv

.PHONY: tests test
tests: test
test: .tox/test.rebuild
	tox $(REBUILD_FLAG) -- "$(ARGS)"

%.rebuild: setup.py requirements.d/*.txt Makefile tox.ini
	$(eval REBUILD_FLAG := --recreate)
	mkdir -p $(shell dirname $@)
	touch $@

.PHONY: docs
docs:
	tox -e docs

.PHONY: clean
clean:
	find -name '*.pyc' | xargs -r rm
	find -name '__pycache__' | xargs -r rm -r
	rm -rf .tox
