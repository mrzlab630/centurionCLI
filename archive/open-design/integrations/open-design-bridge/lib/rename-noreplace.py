#!/usr/bin/env python3
"""Atomically rename one entry without replacing a destination."""

import ctypes
import errno
import os
import sys

RENAME_NOREPLACE = 1
SOURCE_FD = 3
DESTINATION_FD = 4


def safe_name(value: str) -> bool:
    return bool(value) and value not in {".", ".."} and "/" not in value and "\0" not in value


def main() -> int:
    if len(sys.argv) != 3 or not all(safe_name(value) for value in sys.argv[1:]):
        print("rename-noreplace requires two safe entry names", file=sys.stderr)
        return 2

    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        print("renameat2 is unavailable on this Linux runtime", file=sys.stderr)
        return 3

    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    source = os.fsencode(sys.argv[1])
    destination = os.fsencode(sys.argv[2])
    if renameat2(SOURCE_FD, source, DESTINATION_FD, destination, RENAME_NOREPLACE) == 0:
        return 0

    error_number = ctypes.get_errno()
    message = os.strerror(error_number)
    if error_number == errno.EEXIST:
        message = f"File exists: {message}"
    print(f"renameat2(RENAME_NOREPLACE) failed: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
