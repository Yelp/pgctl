.. _advanced:

Advanced Usage
==============

You may (or may not) want these notes after using pgctl for a while.

Services that stop slowly
-------------------------

When you have a service that takes a while to stop, pgctl may incorrectly error out saying that the service left processes behind. By default, pgctl only waits up to two seconds. To tell pgctl to wait a bit longer write a number of seconds into a ``timeout`` file.


.. code:: bash

    echo 10 > playground/uwsgi/timeout
    git add playground/uwsgi/timeout


Handling subprocesses in a bash service
---------------------------------------

If you're unable to use ``exec`` to :ref:`create a single-process service <writing_services>`, you'll need to handle ``SIGTERM`` and kill off your subprocesses yourself. In bash this is tricky. See the example in our test suite for an example of how to do this reliably:

https://github.com/Yelp/pgctl/blob/master/tests/examples/output/playground/ohhi/run
