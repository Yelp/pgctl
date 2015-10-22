FROM ubuntu:trusty

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install \
        make \
        python-virtualenv \
        wget \
        ca-certificates \
        git \
        gcc \
        libc6-dev \
    && apt-get clean

RUN virtualenv /opt/virtualenv
ENV VIRTUAL_ENV=/opt/virtualenv
ENV PATH=/opt/virtualenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# avoids an edge-case bug in virtualenv when using a unknown uid:
ENV PYTHONUSERBASE=/

WORKDIR /code

# at this point, we're on par with circle/travis -- let's install our prerequisites
ADD install CI/install
RUN CI/install/main

# know thy user
USER nobody
ENV USER=nobody
ENV EMAIL=nobody
ENV GIT_COMMITTER_NAME=nobody
ENV HOME=/tmp

# run the tests
ENV TOXENV=python
CMD tox
