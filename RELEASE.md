**NOTE:** This guide is only useful for the owners of the pgctl project.

1. bump `pgctl/__init__.py`
1. `git commit -am "v{{version}}"`
1. `git tag v{{version}} && git push origin master --tags`
1.  upload to pypi
    1. if you need to set up pypi auth, `python setup.py register` and follow the prompts
    1. `python setup.py sdist bdist_wheel`
    1. `twine upload --skip-existing dist/*`
1. `fetch-python-package pgctl` -- upload to pypi.yelpcorp
