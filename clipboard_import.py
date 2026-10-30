"""Read files explicitly copied in Explorer when the user presses Ctrl+V."""
from __future__ import annotations

import ctypes
from ctypes import wintypes


def _read_files(user32, shell32):
    if not user32.IsClipboardFormatAvailable(15):  # CF_HDROP
        return []
    if not user32.OpenClipboard(None):
        return []
    try:
        handle = user32.GetClipboardData(15)
        if not handle:
            return []
        count = shell32.DragQueryFileW(handle, 0xFFFFFFFF, None, 0)
        if not 1 <= count <= 20:
            raise ValueError("Copy between 1 and 20 mod or asset files, or ZIP, 7z and RAR packs.")
        paths = []
        for index in range(count):
            length = shell32.DragQueryFileW(handle, index, None, 0)
            if not 0 < length < 32768:
                raise ValueError("A copied file path is too long or no longer available.")
            buffer = ctypes.create_unicode_buffer(length + 1)
            if shell32.DragQueryFileW(handle, index, buffer, length + 1) != length:
                raise ValueError("The copied file list changed. Copy the files again.")
            paths.append(buffer.value)
        return paths
    finally:
        user32.CloseClipboard()


def copied_files():
    user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    shell32.DragQueryFileW.restype = wintypes.UINT
    before = user32.GetClipboardSequenceNumber()
    paths = _read_files(user32, shell32)
    if before != user32.GetClipboardSequenceNumber():
        raise ValueError("The clipboard changed. Copy the files again, then press Ctrl+V.")
    return paths
