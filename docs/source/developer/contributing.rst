.. _contributing:

Contributor's guide
===================

This page helps you make contributions to the pgctl project.

For a quick primer on using github, see
https://guides.github.com/activities/contributing-to-open-source/

Developer Environment
---------------------
To put yourself into our dev environment, run ``source .activate.sh``.


Documentation
-------------
If you need to make changes to the documentation, they live under docs/source.
For a quick primer on the rst format, see
http://docutils.sourceforge.net/docs/user/rst/quickref.html

If you want to see good examples of other projects' documentation, see:

   * [the Requests
     docs](https://github.com/kennethreitz/requests/tree/master/docs)
   * [the virtualenv docs](https://github.com/pypa/virtualenv/tree/master/docs)

To get a look at your changes, run `make docs` from the root of the project.
This will spin up a http server on port 8088 serving your editted documentation.


Debugging
---------
To get extra debugging output from pgctl, set the ``PGCTL_VERBOSE`` environment variable.
This will cause any tests that assert the *output* of ``pgctl`` to fail, but it often helps finding
mysterious issues.


Run tests
---------

    * make test   ## (should Just Work)
    * tox -e test  ## lose proper --recreate logic
    * ./test  ## `python` must have all test deps
    * py.test  ## lose coverage and linting

Filter which tests to run
-------------------------

    * make test ARGS='-k "test and stop"'
    * tox -e test -- '-k "test and stop"'
    * ./test -k "test and stop"
    * py.test tests -k "test and stop"

Run a particular test
---------------------

    * py.test tests/main_test.py::test_stop

Coverage reports should show all project files as well as test files.


Looking at Coverage
-------------------

It's good practice to look at unit coverage separately from spec
coverage. First,

    make unit test

or:

    make spec test


And in a separate terminal:

    make coverage-server


Complications
-------------

These are the things that make things more complicated than they (seem to) need to be.

A broken setup.py should cause failing tests. Many projects' testing setup will
blissfully pass even if setup.py does nothing whatsoever. In order to avoid
this, I use `changedir` in my tox.ini. Most of the other complexity comes from
this. For example, because I run the code that's inside the virtualenv during
test, it's fiddly to get coverage to report on the right copy of the code.

Subprocess coverage is complicated. coveragepy has some built-in support for
this, but it's not enabled by default. The script at
`tests/testing/install_coverage_pth.py` does the necessary addtional work to
enable the subprocess coverage feature. Because several coverage runs may be
running concurrently, we must be careful to always use coverage in "parallel
mode" and run `coverage combine` afterward.

.. vim:textwidth=79:shiftwidth=3
