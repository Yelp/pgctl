#!/not/executable/bash
# TODO: make aactivator cd to the top directory before sourcing
# TODO: use venv-update to make this much more lightweight
make devenv
export TOP=$PWD
source .tox/devenv/bin/activate
