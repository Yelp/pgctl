Just documenting the things we can do in this codebase:

Run tests:
    * make test   ## (should Just Work)
    * tox -e test  ## lose proper --recreate logic
    * ./test  ## `python` must have all test deps
    * py.test  ## lose coverage and linting

Filter which tests to run:
    * make test ARGS='-k "test and stop"'
    * tox -e test -- -k "test and stop"
    * ./test -k "test and stop"
    * py.test tests -k "test and stop"

Run a particular test:
    * py.test tests/main_test.py::test_stop 
