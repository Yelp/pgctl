from __future__ import absolute_import
from __future__ import unicode_literals


def normalize_newlines(fd):
    r"""
    Twiddle the tty flags such that \n won't get munged to \r\n.
    Details:
        https://docs.python.org/2/library/termios.html
        http://ftp.gnu.org/old-gnu/Manuals/glibc-2.2.3/html_chapter/libc_17.html#SEC362
    """
    import termios as T
    attrs = T.tcgetattr(fd)
    attrs[1] &= ~(T.ONLCR | T.OPOST)
    T.tcsetattr(fd, T.TCSANOW, attrs)
