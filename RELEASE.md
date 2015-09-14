**note:** For maintainers only.

1. ``git checkout upstream/master -b {{branch}}``
2. bump setup.py
2. bump doc versions in docs/source/conf.py
3. ``git commit -m "{{version}}"``
4. ``git tag {{version}}``
5. ``git push --tags``
6. ``git push origin HEAD``
7. Create a pull request
