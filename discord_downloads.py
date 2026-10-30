"""Pick up only newly downloaded files named by the requested Discord post.

No Discord controls, account files, clipboard, or network requests are accessed.
The user initiates the download in Discord. Actual installation still needs the
normal review. Existing downloads and symlinks are never selected automatically.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

from discord_posts import preview_name


def downloads_directory():
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                        ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

        folder_id = GUID(0x374DE290, 0x123F, 0x4565, (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
        result = ctypes.c_wchar_p()
        shell = ctypes.windll.shell32
        shell.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
        shell.SHGetKnownFolderPath.restype = ctypes.c_long
        ctypes.windll.ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        if shell.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(result)) == 0:
            try:
                return Path(result.value)
            finally:
                ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(result, ctypes.c_void_p))
    return Path.home() / "Downloads"


def matches_download(actual, expected):
    if not preview_name(expected):
        return False
    stem, ext = os.path.splitext(expected)
    return bool(re.fullmatch(re.escape(stem) + r"(?: \([1-9][0-9]{0,5}\))?" + re.escape(ext), actual, re.I))


def writer_closed(path):
    if os.name != "nt":
        return True
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.windll.kernel32
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                   wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    # Permit other readers, but do not read a file while a downloader holds it for writing.
    handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)
    if handle == wintypes.HANDLE(-1).value:
        return False
    kernel.CloseHandle(handle)
    return True


class DownloadWatch:
    def __init__(self, names, folder=None, clock=time.monotonic, available=writer_closed):
        self.names = tuple(dict.fromkeys(name for name in names if preview_name(name)))
        if not self.names or len(self.names) > 20:
            raise ValueError("No supported preview attachments were found")
        self.folder = Path(folder) if folder is not None else downloads_directory()
        self.clock, self.available = clock, available
        self.started = self.clock()
        self.baseline = self._scan()
        self.stable = {}

    def _scan(self):
        found = {}
        try:
            with os.scandir(self.folder) as entries:
                for entry in entries:
                    if (not any(matches_download(entry.name, name) for name in self.names)
                            or entry.is_symlink() or not entry.is_file(follow_symlinks=False)):
                        continue
                    path = Path(entry.path)
                    if hasattr(os.path, "isjunction") and os.path.isjunction(path):
                        continue
                    stat = entry.stat(follow_symlinks=False)
                    if 0 < stat.st_size <= 32 * 1024 * 1024:
                        found[str(path)] = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        except OSError:
            pass
        return found

    def poll(self):
        if self.clock() - self.started > 600:
            return {"status": "choose", "message": "Automatic download pickup has timed out. Choose the downloaded file to continue."}
        current = self._scan()
        fresh = {path: stamp for path, stamp in current.items() if self.baseline.get(path) != stamp}
        now = self.clock()
        ready = []
        for name in self.names:
            matching = [path for path in fresh if matches_download(Path(path).name, name)]
            if len(matching) > 1:
                return {"status": "choose", "message": "Several new downloads match this post. Choose the file you want to import."}
            if not matching:
                return {"status": "waiting"}
            path = matching[0]
            prior = self.stable.get(path)
            if prior is None or prior[0] != fresh[path]:
                self.stable[path] = (fresh[path], now)
                return {"status": "waiting"}
            if now - prior[1] < 1 or not self.available(path):
                return {"status": "waiting"}
            ready.append(path)
        return {"status": "ready", "paths": ready}
