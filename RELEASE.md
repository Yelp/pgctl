**NOTE:** This guide is only useful for the owners of the pgctl project.

1. `git fetch`
1. `git checkout upstream/master -b release-v{{version}}`
1. bump `pgctl/__init__.py`
1. `git commit -am "This is v{{version}}"`
1. Create a pull request
1. Wait for review / merge
1. go to https://github.com/Yelp/pgctl/releases and add a tag
1. `git fetch yelp --tags`
1. `git checkout v1.1.0`   --  for example
1.  upload to pypi
    1. if you need to set up pypi auth, `python setup.py register` and follow the prompts
    1. `python setup.py sdist bdist_wheel`
    1. `twine upload --skip-existing dist/*`
1. `fetch-python-package pgctl` -- upload to pypi.yelpcorp
