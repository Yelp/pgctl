.. _advanced:

Advanced Usage
==============

You may (or may not) want these notes after using pgctl for a while.

Services that stop slowly
-------------------------

When you have a service that takes a while to stop, pgctl may incorrectly error out saying that the service left processes behind. By default, pgctl only waits up to two seconds. To tell pgctl to wait a bit longer write a number of seconds into a ``timeout-stop`` file.


.. code:: bash

    $ echo 10 > playground/uwsgi/timeout-stop
    $ git add playground/uwsgi/timeout-stop


Services that start slowly
--------------------------

Similarly, if pgctl needs to be told to wait longer to start your service, write a ``timeout-ready`` file.

If there's a significant period between when the service has started (up) and when it's actually doing it's job (ready),
or if your service sometimes stops working even when it's running, create a runnable ``ready`` script in the service
directory and prefix your service command with our ``pgctl-poll-ready`` helper script.  ``pgctl-poll-ready`` will run
the ``ready`` script repeatedly to determine when your service is actually ready. As an example:


.. code:: bash

    $ cat playground/uwsgi/run
    make -C ../../ minimal  # the build takes a few seconds
    exec pgctl-poll-ready ../../bin/start-dev

    $ cat playground/uwsgi/ready
    exec curl -s localhost:9003/status

    $ cat playground/uwsgi/timeout-ready
    30


Handling subprocesses in a bash service
---------------------------------------

If you're unable to use ``exec`` to :ref:`create a single-process service <writing_services>`, you'll need to handle ``SIGTERM`` and kill off your subprocesses yourself. In bash this is tricky. See the example in our test suite for an example of how to do this reliably:

https://github.com/Yelp/pgctl/blob/master/tests/examples/output/playground/ohhi/run
