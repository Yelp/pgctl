.. _quickstart:

Quickstart
==========

This page attempts to be a quick-and-dirty guide to getting started with pgctl.


Setting up
----------


The minimal setup for pgctl is a ``playground`` directory containing the services
you want to run.  A service consists of a directory with a ``run`` script. The
script should run in the foreground.


::

   $ cat playground/date/run
   date > now.date


Once this is in place, you can start your playground and see it run.

.. TODO-TEST: assert that this is accurate.

::

  $ pgctl start
  $ pgctl logs
  [webapp] Serving HTTP on 0.0.0.0 port 36474 ...

  $ curl 


Aliases
------------------------
With no arguments, ``pgctl start`` is equivalent to ``pgctl start default``.
By default, ``default`` maps to a list of all services.
You can configure what ``default`` means via ``playground/config.yaml``:

.. note that yaml has really bad/no styling in pygments

.. code-block:: yaml

    aliases:
        default:
            - service1
            - service2


You can also add other aliases this way. When you name an alias, it simply
expands to the list of configured services, so that ``pgctl start A-and-B``
would be entirely equivalent to ``pgctl start A B``.
