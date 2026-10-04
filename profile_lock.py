"""An OS-owned profile lock, released on normal exit or process termination."""
import errno
import os
from pathlib import Path


class ProfileInUse(Exception):
    pass


def acquire_profile_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
            raise ProfileInUse('Diese Profildatei ist bereits in einer laufenden App geöffnet.') from exc
        raise
    return handle
