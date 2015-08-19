Developers
==========


Directory Structure
-------------------

::

    $ pwd
    /home/<user>/<project>

    $ tree playground/
    playground/
    ├── service1
    │   ├── down
    │   ├── run
    │   ├── stderr.log
    │   ├── stdout.log
    │   └── supervise -> ~/.run/pgctl/home/<user>/<project>/playground/service1/supervise
    ├── service2
    │   ├── down
    │   ├── run
    │   ├── stderr.log
    │   ├── stdout.log
    │   └── supervise -> ~/.run/pgctl/home/<user>/<project>/playground/service2/supervise
    └── service3
        ├── down
        ├── run
        ├── stderr.log
        ├── stdout.log
        └── supervise -> ~/.run/pgctl/home/<user>/<project>/playground/service3/supervise

There are a few points to note: logging, services, state, symlinking.  

logging
+++++++
stdin and stdout will be captured from the supervised process and written to log files under 
the service directory.  The user will be able to use the ``pgctl logs`` command to aggregate 
these logs in a readable form.

services
++++++++
All services are located under the playground directory.

state
+++++
We are using daemontools for process management and call the daemontools ``supervise`` command directly.
It was a design decision to not use ``svscan`` to automatically supervise all services.  This was due
to inflexability with logging (by default stdout is only logged).  To ensure that every service 
is in a consistent state, a down file is added to each service directory (man supervise) if it does not
already exist.

symlinking
++++++++++
Currently ``pip install .`` calls shutil.copy to copy all files in the current project when in the project's
base directory.  Having pipes present in the projects main directory attempts to copy the pipe and deadlocks.
To remedy this situation, we have symlinked the supervise directory to the user's home directory to prevent
any pip issues.


Design Decisions
----------------

Design of debug
+++++++++++++++

Unsupervise all things when down
++++++++++++++++++++++++++++++++
