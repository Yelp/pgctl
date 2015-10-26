.. _bugs:

Bug Log
=======

This documents current and past bugs in the project.
This is helpful when during future debugging sessions.


Current bugs -- 2015-10-26
--------------------------

Currently the coverage report improperly shows missing coverage, but only under jenkins / circleCI.
Local testing and travis don't seem to have this issue.

I've found some clues:

    * only lines run *directly* by the xdist workers goes missing; all subprocess coverage is reliable.
    * the xdist worker does write out its coverage file on time, it's just (mostly) empty.
    * from looking at the coverage debugging trace: the coverage drops out at this line:
          https://bitbucket.org/hpk42/execnet/src/50f88cb892d/execnet/gateway_base.py#gateway_base.py-1072
    * TODO: does this reproduce using coverage<4.0 ?


### Circle CI debugging

To grab files from a circleCI run: (for example)

    rsync -Pav  -e 'ssh -p 64785' ubuntu@54.146.184.147:pgctl/coverage.bak.2015-10-24_18:28:36.937047774 .
