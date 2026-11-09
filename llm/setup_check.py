"""(f532) What this machine has, for the load screen's lines (llm/launch.py): its memory. The card and its memory come from the model
server's own device list (llm/runtime.py parse_devices). Nothing here installs or downloads anything: the game ships its own model server
and model files (data/runtime/server.yaml, tools/fetch_runtime.py), and the load screen says what is missing in the owner's words."""

import os
import sys


def ram_gb() -> float:
    """The machine's memory in gigabytes; 0.0 when it cannot be read."""
    try:
        if sys.platform == "win32":
            import ctypes

            class MEM(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong), ("avail", ctypes.c_ulonglong),
                            ("pt", ctypes.c_ulonglong), ("pa", ctypes.c_ulonglong), ("vt", ctypes.c_ulonglong), ("va", ctypes.c_ulonglong),
                            ("ext", ctypes.c_ulonglong)]
            m = MEM(); m.length = ctypes.sizeof(MEM)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.total / 2 ** 30
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30
    except Exception:
        return 0.0
