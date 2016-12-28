These are small tasks that I'd like to get done, but not today:

 * move `tests/examples/*/playground/*` to `examples/*`
 * merge 'stdout.log' and 'stderr.log' to simply 'log'
    * colorize/prefix stderr lines?
    * add timestamps?
 * colorize pgctl output

BUGS
 * removing 'ready' leaves notification-fd behind, very confusing
 * an instantly-failing service is detected as ready

UX
 * an "insecure" config file is rejected quietly, resulting in
   unexpected behavior -- very hard to debug
