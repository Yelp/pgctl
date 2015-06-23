.. stolen from some good examples:
   https://github.com/pypa/virtualenv/edit/master/docs/index.rst
   https://github.com/kennethreitz/requests/edit/master/docs/index.rst

.. rst quick reference:
   http://docutils.sourceforge.net/docs/user/rst/quickref.html


pgctl: the playground controller
================================
`Issues <https://github.com/pypa/virtualenv/issues>`_ |
`Github <https://github.com/pypa/virtualenv>`_
.. TODO `PyPI <https://pypi.python.org/pypi/virtualenv/>`_ |

Release v\ |version|. (:ref:`Installation <install>`)

Introduction
------------

``pgctl`` is an `MIT Licensed
<https://github.com/Yelp/pgctl/blob/master/COPYING>`_ tool to manage developer "playgrounds".

Often projects have various processes that should run in the backround
(*services*) during development. These services amount to a miniature staging
environment that we term *playground*. Each service must have a well-defined
state at all times (it should be starting, up or down), and should be
independantly restartable and debuggable.

``pgctl`` aims to solve this problem in a unified, language-agnostic
framework (although the tool happens to be written in Python).

.. TODO-DOC: tiny demo

Feature Support
---------------
  
  -  User-friendly Command Line Interface
  -  Simple Configuration
  -  Python 2.6—3.4
  -  pypy and pypy3


User Guide
----------

This part of the documentation, which is mostly prose, begins with some
background information about Requests, then focuses on step-by-step
instructions for getting the most out of Requests.

.. toctree::
   :maxdepth: 2

   user/install
   user/quickstart
   user/advanced

API Documentation
-----------------

If you are looking for information on a specific function, class or method,
this part of the documentation is for you.

.. toctree::
   :maxdepth: 2

   api/pgctl


Contributor Guide
-----------------

If you want to contribute to the project, this part of the documentation is for
you.

.. toctree::
   :maxdepth: 1

   dev/contributing
   dev/philosophy
   dev/todo
   dev/authors


.. vim:textwidth=79:shiftwidth=3
