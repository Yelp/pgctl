**note:** For maintainers only.

1. ``git checkout upstream/master -b {{branch}}``
2. bump setup.py
3. bump doc versions in docs/source/conf.py
4. ``git commit -m "{{version}}"``
5. Create a pull request
6. Wait for review / merge
7. go to https://github.com/Yelp/pgctl/releases and add a tag
8. ``git fetch yelp --tags``
9. ``git checkout v1.1.0``   --  for example
10. ``python setup.py sdist upload`` -- upload to pypi
    10.1. if you need to set up pypy auth, see https://docs.python.org/2/distutils/packageindex.html#the-python-package-index-pypi
    10.2. run `chmod 600 ~/.pypirc` *before* you write to it
11. ``fetch_python_package pgctl`` -- upload to pypi.yelpcorp:  
