.. _install:

Installation
============

This part of the documentation covers the installation of pgctl.
The first step to using any software package is getting it properly installed.


Distribute & Pip
----------------

Installing pgctl is simple with `pip <https://pip.pypa.io>`_, just run
this in your terminal::

    $ pip install pgctl


Get the Code
------------

pgctl is actively developed on GitHub, where the code is
`always available <https://github.com/Yelp/pgctl>`_.

You can either clone the public repository::

    $ git clone git://github.com/yelp/pgctl.git

Download the `tarball <https://github.com/yelp/pgctl/tarball/master>`_::

    $ curl -OL https://github.com/yelp/pgctl/tarball/master

Or, download the `zipball <https://github.com/yelp/pgctl/zipball/master>`_::

    $ curl -OL https://github.com/yelp/pgctl/zipball/master

Once you have a copy of the source, you can embed it in your Python package,
or install it into your site-packages easily::

    $ python setup.py install
