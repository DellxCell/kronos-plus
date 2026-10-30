"""Start the game through Kronos's existing launcher Play control."""
from __future__ import annotations

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import os
import threading
import time


@dataclass(frozen=True)
class Controls:
    window: int
    play: int
    tab: int
    pid: int
    enabled: bool
    visible: bool


class NativeLauncher:
    # Observed native launcher controls: 117 is the Play page; 112 starts the game.
    PLAY, PLAY_TAB = 112, 117

    def __init__(self):
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        definitions = {
            "EnumWindows": ([self.callback_type, wintypes.LPARAM], wintypes.BOOL),
            "GetWindowThreadProcessId": ([wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.DWORD),
            "GetDlgItem": ([wintypes.HWND, ctypes.c_int], wintypes.HWND),
            "GetParent": ([wintypes.HWND], wintypes.HWND),
            "GetWindowTextW": ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            "GetClassNameW": ([wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            "IsWindowVisible": ([wintypes.HWND], wintypes.BOOL),
            "IsWindowEnabled": ([wintypes.HWND], wintypes.BOOL),
            "ShowWindow": ([wintypes.HWND, ctypes.c_int], wintypes.BOOL),
            "SetForegroundWindow": ([wintypes.HWND], wintypes.BOOL),
            "SendMessageTimeoutW": ([wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                     wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)], ctypes.c_ssize_t),
        }
        for name, (args, result) in definitions.items():
            function = getattr(self.user, name)
            function.argtypes, function.restype = args, result
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                         wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.restype = wintypes.BOOL

    def text(self, hwnd, class_name=False):
        buffer = ctypes.create_unicode_buffer(512)
        function = self.user.GetClassNameW if class_name else self.user.GetWindowTextW
        function(hwnd, buffer, len(buffer))
        return buffer.value

    def process_path(self, pid):
        handle = self.kernel.OpenProcess(0x1000, False, pid)  # query limited information only
        if not handle:
            return None
        try:
            buffer, length = ctypes.create_unicode_buffer(32768), wintypes.DWORD(32768)
            return buffer.value if self.kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)) else None
        finally:
            self.kernel.CloseHandle(handle)

    def control(self, hwnd, launcher):
        pid = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        actual = self.process_path(pid.value)
        if not actual or os.path.normcase(os.path.realpath(actual)) != os.path.normcase(os.path.realpath(launcher)):
            return None
        if not self.user.IsWindowVisible(hwnd):
            return None
        play, tab = self.user.GetDlgItem(hwnd, self.PLAY), self.user.GetDlgItem(hwnd, self.PLAY_TAB)
        for button in (play, tab):
            child_pid = wintypes.DWORD()
            self.user.GetWindowThreadProcessId(button, ctypes.byref(child_pid))
            if (not button or child_pid.value != pid.value or self.user.GetParent(button) != hwnd
                    or self.text(button) != "Play" or self.text(button, True).casefold() != "button"):
                return None
        return Controls(hwnd, play, tab, pid.value,
                        bool(self.user.IsWindowEnabled(hwnd) and self.user.IsWindowEnabled(play)),
                        bool(self.user.IsWindowVisible(play)))

    def find(self, launcher):
        found = []
        @self.callback_type
        def each(hwnd, _):
            control = self.control(hwnd, launcher)
            if control:
                found.append(control)
            return True
        self.user.EnumWindows(each, 0)
        if len(found) > 1:
            raise ValueError("More than one Kronos launcher is open. Close the extra launcher and try Play again.")
        return found[0] if found else None

    def command(self, original, launcher, tab=False):
        current = self.control(original.window, launcher)
        if not current or current.pid != original.pid or current.play != original.play or current.tab != original.tab:
            raise ValueError("The Kronos launcher changed before Play could be activated. Try again.")
        button = current.tab if tab else current.play
        if (not self.user.IsWindowEnabled(current.window) or not self.user.IsWindowEnabled(button)
                or not self.user.IsWindowVisible(button)):
            raise ValueError("Kronos isn't ready to play yet. Finish any setup or open dialog in its launcher.")
        self.user.ShowWindow(current.window, 9)  # restore without moving the cursor
        self.user.SetForegroundWindow(current.window)
        result = ctypes.c_size_t()
        # The same WM_COMMAND / BN_CLICKED notification emitted by this native button.
        # Send it once; a timeout has an unknown outcome and must never be retried.
        if not self.user.SendMessageTimeoutW(current.window, 0x0111, self.PLAY_TAB if tab else self.PLAY,
                                              button, 0x22, 2000, ctypes.byref(result)):
            raise ValueError("Windows couldn't activate Kronos's Play button. Check its launcher before trying again.")


class GameStarter:
    def __init__(self):
        self.lock = threading.Lock()

    def start(self, launcher, running, open_launcher=os.startfile, native=None,
              clock=time.monotonic, pause=time.sleep, ready_timeout=15, game_timeout=30):
        if not self.lock.acquire(blocking=False):
            return {"status": "starting"}
        try:
            if running():
                return {"status": "playing"}
            native = native or NativeLauncher()
            control = native.find(launcher)
            if not control:
                open_launcher(launcher)
            deadline, page_requested = clock() + ready_timeout, False
            while clock() < deadline:
                if running():
                    return {"status": "playing"}
                control = native.find(launcher)
                if control and control.enabled:
                    if control.visible:
                        break
                    if not page_requested:
                        native.command(control, launcher, tab=True)
                        page_requested = True
                pause(0.2)
            else:
                return {"error": "Kronos's Play button isn't ready. Check the launcher for setup, updates or an open dialog."}
            # Recheck after waiting so a game the user started isn't launched twice.
            if running():
                return {"status": "playing"}
            native.command(control, launcher)
            deadline = clock() + game_timeout
            while clock() < deadline:
                if running():
                    return {"status": "started"}
                pause(0.25)
            return {"error": "Kronos received Play, but the game hasn't appeared. Check its launcher for an error before trying again."}
        except (OSError, ValueError) as error:
            if getattr(error, "winerror", None) == 1223:
                return {"error": "The Kronos launcher needs your OK to start. Click Play again and choose Yes."}
            return {"error": str(error)}
        finally:
            self.lock.release()


STARTER = GameStarter()
