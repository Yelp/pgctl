**note:** For maintainers only.

1. ``git checkout upstream/master -b {{branch}}``
2. bump setup.py
2. bump doc versions in docs/source/conf.py
3. ``git commit -m "{{version}}"``
4. ``git tag {{version}}``
5. ``git push --tags``
6. ``git push origin HEAD``
7. Create a pull request
8. Wait for review / merge
9. upload to pypi: python setup.py sdist upload
    9.1. if you need to set up pypy auth, see https://docs.python.org/2/distutils/packageindex.html#the-python-package-index-pypi
    9.2. run `chmod 600 ~/.pypirc` *before* you write to it
10. upload to pypi.yelpcorp:  `fetch_python_package pgctl`
