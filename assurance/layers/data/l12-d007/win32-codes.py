"""L12-D007: capture the raw Win32 error of a READ-ONLY CreateFileW(OPEN_EXISTING) for the name-class
conditions, using the same path forms Node/libuv uses. Nothing is created, written or deleted.

    python win32-codes.py <existing directory inside the project root>
"""

import ctypes
import os
import sys
from ctypes import wintypes

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
k32.CreateFileW.restype = wintypes.HANDLE
GENERIC_READ, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS = 0x80000000, 3, 0x02000000
INVALID = wintypes.HANDLE(-1).value

base = os.path.abspath(sys.argv[1])
assert os.path.isdir(base)
cases = {
    "name-too-long (plain)": os.path.join(base, "n" * 300),
    "name-too-long (\\\\?\\ namespaced, as libuv)": "\\\\?\\" + os.path.join(base, "n" * 300),
    "invalid-name x<y": os.path.join(base, "x<y"),
    "ntfs-stream-syntax f:stream:bad (no file f)": base + os.sep + "f:stream:bad",
}
for label, p in cases.items():
    h = k32.CreateFileW(p, GENERIC_READ, 7, None, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, None)
    err = ctypes.get_last_error()
    if h != INVALID:
        k32.CloseHandle(h)
        print(f"{label}: OPENED (unexpected)")
    else:
        print(f"{label}: Win32 {err}")
