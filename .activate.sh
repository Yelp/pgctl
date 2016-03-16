#!/not/executable/bash
# TODO: make aactivator cd to the top directory before sourcing
# TODO: use venv-update to make this much more lightweight
make venv
export TOP=$PWD
source venv/bin/activate
