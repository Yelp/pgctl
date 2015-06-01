#!/not/executable/bash
export TOP=$(dirname $(readlink -f $_))
make venv
source venv-pgctl/bin/activate
