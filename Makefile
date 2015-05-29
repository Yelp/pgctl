
REBUILD_FLAG =

.PHONY: all
all: venv test

.PHONY: venv
venv: .venv.touch
	tox -e venv $(REBUILD_FLAG)

.PHONY: tests test
tests: test
test: .venv.touch
	tox $(REBUILD_FLAG)

.venv.touch: setup.py requirements.d/*.txt
	$(eval REBUILD_FLAG := --recreate)
	touch .venv.touch

.PHONY: clean
clean:
	find -name '*.pyc' | xargs -r rm
	find -name '__pycache__' | xargs -r rm -r
	rm -rf .tox
	rm -rf ./venv-*
	rm -f .venv.touch
