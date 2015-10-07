**note:** For maintainers only.

1. `git checkout upstream/master -b {{branch}}`
1. bump setup.py
1. bump doc versions in docs/source/conf.py
1. `git commit -m "{{version}}"`
1. Create a pull request
1. Wait for review / merge
1. go to https://github.com/Yelp/pgctl/releases and add a tag
1. `git fetch yelp --tags`
1. `git checkout v1.1.0`   --  for example
1.  upload to pypi
    1. if you need to set up pypy auth, `python setup.py register` and follow the prompts
    1. `python setup.py sdist`
    1. `twine upload --skip-existing dist/*`
1. `fetch_python_package pgctl` -- upload to pypi.yelpcorp:  
