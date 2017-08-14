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
  $ pgctl log
  [webapp] Serving HTTP on 0.0.0.0 port 36474 ...

  $ curl


.. _writing_services:

Writing Playground Services
-----------------------------
``pgctl`` works best with a single process. When writing a ``run`` script in
bash, use the ``exec`` statement to replace the shell with your process. This
avoids a process tree with bash as the parent of your service. Having a single
process allows simple management of state and proper signalling for stopping
the service.

Bad: (don't do this!)

.. code:: bash

    #!/bin/bash
    sleep infinity  # creates a new process

Good: (do it this way!)

.. code:: bash

    #!/bin/bash
    exec sleep infinity  # replaces the *current* process


Without the exec, stopping the service will kill `bash` but the `sleep` process
will be left behind.  This kind of process-tree management is too complex for
``pgctl`` to auto-magically fix it for you, but it will let you know if it
becomes a problem:

.. code:: bash

    $ pgctl restart
    Stopping: sleeper
    Stopped: sleeper
    ERROR: We sent SIGTERM, but these processes did not stop:
                        USER        PID ACCESS COMMAND
    playground/sleeper:    buck     2847827 f.c.. sleep

    To fix this temporarily, run: pgctl stop playground/sleeper --force
    To fix it permanently, see:
        http://pgctl.readthedocs.org/en/latest/user/quickstart.html#writing-playground-services


.. _aliases:

Aliases
------------------------

With no arguments, ``pgctl start`` is equivalent to ``pgctl start default``.
By default, ``default`` maps to a list of all services.
You can configure what ``default`` means via ``pgctl.yaml``:

.. note that yaml has really bad/no styling in pygments

.. code-block:: yaml

    aliases:
        default:
            - service1
            - service2


You can also add other aliases this way. When you name an alias, it simply
expands to the list of configured services, so that ``pgctl start A-and-B``
would be entirely equivalent to ``pgctl start A B``.
