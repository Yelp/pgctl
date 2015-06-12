REBUILD_FLAG =

.PHONY: all
all: venv test

.PHONY: venv
venv:  .tox/venv
.tox/venv: .venv.touch
	mkdir -p .tox
	rm -rf .tox/pgctl
	virtualenv .tox/pgctl --python=python2.7
	.tox/pgctl/bin/pip install --upgrade pip
	.tox/pgctl/bin/pip install --upgrade -r requirements.d/dev.txt
	ln -sf pgctl .tox/venv

.PHONY: tests test
tests: test
test: .venv.touch
	tox $(REBUILD_FLAG)

.venv.touch: setup.py requirements.d/*.txt Makefile tox.ini
	$(eval REBUILD_FLAG := --recreate)
	touch .venv.touch

.PHONY: clean
clean:
	find -name '*.pyc' | xargs -r rm
	find -name '__pycache__' | xargs -r rm -r
	rm -rf .tox
	rm -f .venv.touch
