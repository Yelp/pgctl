.. stolen from some good examples:
   https://github.com/pypa/virtualenv/edit/master/docs/index.rst
   https://github.com/kennethreitz/requests/edit/master/docs/index.rst

.. rst quick reference:
   http://docutils.sourceforge.net/docs/user/rst/quickref.html


pgctl: the playground controller
================================
`Issues <https://github.com/yelp/pgctl/issues>`_ |
`Github <https://github.com/yelp/pgctl>`_ |
`PyPI <https://pypi.python.org/pypi/pgctl/>`_

Release v\ |version|. (:ref:`Installation <install>`)

Introduction
------------

``pgctl`` is an `MIT Licensed
<https://github.com/Yelp/pgctl/blob/master/COPYING>`_ tool to manage developer "playgrounds".

Often projects have various processes that should run in the backround
(*services*) during development. These services amount to a miniature staging
environment that we term *playground*. Each service must have a well-defined
state at all times (it should be starting, up, stopping, or down), and should be
independantly restartable and debuggable.

``pgctl`` aims to solve this problem in a unified, language-agnostic
framework (although the tool happens to be written in Python).


As a simple example, let's say that we want a `date` service in our playground,
that ensures our `now.date` file always has the current date. 

::

   $ cat playground/date/run
   date > now.date

   $ pgctl start
   $ pgctl status
   date -- up (0 seconds)

   $ cat now.date
   Fri Jun 26 15:21:26 PDT 2015

   $ pgctl stop
   $ pgctl status
   date -- down (0 seconds)


Feature Support
---------------
  
  -  User-friendly Command Line Interface
  -  Simple Configuration
  -  Python 2.7—3.5


User Guide
----------

This part of the documentation covers the step-by-step
instructions and usage of ``pgctl`` for getting started quickly.

.. toctree::
   :maxdepth: 2

   user/install
   user/quickstart
   user/usage
   user/advanced

API Documentation
-----------------

If you are looking for information on a specific function, class or method,
this part of the documentation is for you.

.. toctree::
   :maxdepth: 2

   api


Contributor Guide
-----------------

If you want to contribute to the project, this part of the documentation is for
you.

.. toctree::
   :maxdepth: 2
   :glob:

   developer/contributing
   developer/design
   developer/bugs


.. vim:textwidth=79:shiftwidth=3
