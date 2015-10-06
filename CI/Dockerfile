FROM ubuntu:trusty

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install \
        make \
        python-virtualenv \
        wget \
        lsof \
        ca-certificates \
    && apt-get clean

RUN virtualenv /opt/virtualenv
ENV VIRTUAL_ENV=/opt/virtualenv
ENV PATH=/opt/virtualenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /code

# at this point, we're on par with circle/travis
ADD install CI/install
RUN CI/install/main
ENV TOXENV=python
ENV USER=nobody
CMD tox
