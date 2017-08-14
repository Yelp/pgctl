Sub-Commands
============

``pgctl`` has eight basic commands: ``start``, ``stop``, ``restart``, ``debug``, ``status``, ``log``, ``reload``, ``config``

.. note::

    With no arguments, ``pgctl <cmd>`` is equivalent to ``pgctl <cmd> default``.
    By default, default maps to all services.  See :ref:`aliases`.

start
~~~~~

::

    $ pgctl start <service=default>

Starts a specific service, group of services, or all services.  This command is blocking until all services have successfully reached the up state.  ``start`` is idempotent.

stop
~~~~

::

    $ pgctl stop <service=default>

Stops a specific service, group of services, or all services.  This command is blocking until all services have successfully reached the down stated.  ``stop`` is idempotent.

restart
~~~~~~~

::

    $ pgctl restart <service=default>

Stops and starts specific service, group of services, or all services.  This command is blocking until all services have successfully reached the down stated.

debug
~~~~~

::

    $ pgctl debug <service=default>

Runs a specific service in the foreground.

status
~~~~~~

::

    $ pgctl status <service=default>
    <service> (pid <PID>) -- up (0 seconds)

Retrieves the state, PID, and time in that state of a specific service, group of services, or all services.


log
~~~

::

    $ pgctl log <service=default>

Retrieves the stdout and stderr for a specific service, group of services, or all services.

reload
~~~~~~

::

    $ pgctl reload <service=default>

Reloads the configuration for a specific service, group of services, or all services.

config
~~~~~~

::

    $ pgctl config <service=default>

Prints out a configuration for a specific service, group of services, or all services.
