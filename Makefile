.PHONY: all
all: devenv test

.PHONY: devenv
devenv:  .tox/devenv
.tox/devenv: .tox/pgctl 
	# it's simpler to not try to make tox do this.
	virtualenv --python=python2.7 .tox/pgctl
	.tox/pgctl/bin/pip install --upgrade -r requirements.d/dev.txt
	ln -sf pgctl .tox/devenv

.PHONY: tests test
tests: test
test: .tox/py27
	tox -e py27 -- $(ARGS)

.PHONY: integration unit
integration:
	$(eval ARGS := -k integration)
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
	find -name '*.pyc' | xargs -r rm
	find -name '__pycache__' | xargs -r rm -r
	rm -rf .tox
	rm -rf docs/build



# disable default implicit rules
.SUFFIXES:
%: %,v
%: RCS/%,v
%: RCS/%
%: s.%
%: SCCS/s.%
