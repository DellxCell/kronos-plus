"""Read attachment links from a requested Kronos post in the user's Discord window.

The reader uses Windows accessibility, not Discord credentials or private APIs.
It never clicks, types, sends messages, or changes the clipboard. Run the Windows
reader in a short-lived child process so a stalled accessibility provider cannot
hold the app's UI thread.
"""

from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
from dataclasses import dataclass
from content_packs import ASSET_EXTENSIONS, IMAGE_EXTENSIONS

GUILD_ID = "1564034358094864515"
FORUM_ID = "1564893232985415700"
ASSETS_FORUM_ID = "1564893868724588645"
FORUM_IDS = {FORUM_ID, ASSETS_FORUM_ID}
DISCORD_HOSTS = {"discord.com", "ptb.discord.com", "canary.discord.com", "discordapp.com"}
FILE_HOSTS = {"cdn.discordapp.com", "media.discordapp.net"}
FILE_EXTENSIONS = {".gsc", ".zip", ".rar", ".7z", ".gscc"} | ASSET_EXTENSIONS
SNOWFLAKE = re.compile(r"\d{17,20}\Z")


@dataclass(frozen=True)
class PostLink:
    guild: str
    forum: str | None
    thread: str | None
    message: str | None = None

    @property
    def desktop_path(self):
        if self.forum:
            path = f"{self.guild}/{self.forum}"
            if self.thread:
                path += f"/threads/{self.thread}"
        else:
            path = f"{self.guild}/{self.thread}"
        if self.message:
            path += "/" + self.message
        return path

    @property
    def url(self):
        return "https://discord.com/channels/" + self.desktop_path


def parse_post_link(url: str) -> PostLink | None:
    try:
        parts = urllib.parse.urlsplit((url or "").strip().strip("<>"))
        if parts.scheme != "https" or parts.hostname not in DISCORD_HOSTS or parts.username or parts.password:
            return None
        if parts.port not in (None, 443):
            return None
        path = parts.path.strip("/").split("/")
        if len(path) < 3 or path[0] != "channels" or not all(SNOWFLAKE.fullmatch(p) for p in path[1:3]):
            return None
        guild, channel = path[1:3]
        if len(path) in (5, 6) and path[3] == "threads" and channel in FORUM_IDS:
            thread = path[4]
            message = path[5] if len(path) == 6 else None
            if not SNOWFLAKE.fullmatch(thread) or (message and not SNOWFLAKE.fullmatch(message)):
                return None
            return PostLink(guild, channel, thread, message)
        if len(path) == 3:
            return PostLink(guild, channel if channel in FORUM_IDS else None, None if channel in FORUM_IDS else channel)
        if len(path) == 4 and SNOWFLAKE.fullmatch(path[3]):
            if channel in FORUM_IDS:
                return PostLink(guild, channel, path[3])
            return PostLink(guild, None, channel, path[3])
    except (ValueError, TypeError, AttributeError):
        pass
    return None


def attachment(url: str, label: str = "", allow_images=True) -> dict | None:
    try:
        parts = urllib.parse.urlsplit(url)
        if (parts.scheme != "https" or parts.hostname not in FILE_HOSTS or parts.username or parts.password
                or parts.port not in (None, 443) or not parts.path.startswith("/attachments/") or len(url) > 8192):
            return None
        name = urllib.parse.unquote(parts.path.rsplit("/", 1)[-1])
        extension = os.path.splitext(name)[1].lower()
        if not name or extension not in FILE_EXTENSIONS or (extension in IMAGE_EXTENSIONS and not allow_images):
            return None
        return {"name": name, "url": url, "size": None}
    except (ValueError, TypeError, AttributeError):
        return None


def select_snapshot(target: PostLink, snapshot: dict) -> dict:
    """Validate the reader result again in the parent process."""
    if not isinstance(snapshot, dict):
        return {"status": "waiting"}
    active = parse_post_link(snapshot.get("url", ""))
    if (target.guild != GUILD_ID or not active or active.guild != GUILD_ID or active.forum not in FORUM_IDS
            or (target.forum and active.forum != target.forum)
            or (target.thread and active.thread != target.thread)):
        return {"status": "waiting", "message": "Opening the requested Kronos post in Discord…"}
    if not active.thread:
        return {"status": "pick_post", "message": "Choose a mod or asset post in the open Discord forum."}
    messages = snapshot.get("messages", [])
    if not isinstance(messages, list):
        messages = []
    selected = [message for message in messages[:1000]
                if isinstance(message, dict) and message.get("thread_id") == active.thread
                and isinstance(message.get("message_id"), str) and SNOWFLAKE.fullmatch(message["message_id"])
                and (not target.message or message["message_id"] == target.message)]
    if not selected:
        return {"status": "waiting", "message": "Waiting for the post's messages to appear in Discord…"}
    files, seen = [], set()
    for message in selected:
        candidates = message.get("links", [])
        if not isinstance(candidates, list):
            continue
        for candidate in candidates[:100]:
            item = attachment(candidate.get("url", ""), allow_images=active.forum == ASSETS_FORUM_ID) if isinstance(candidate, dict) else None
            if item:
                key = urllib.parse.urlsplit(item["url"]).path
                if key not in seen:
                    seen.add(key)
                    files.append(item)
    if not files:
        return {"status": "empty", "waiting": target.message is None,
                "message": "No mod or asset attachment is loaded yet. Scroll through this post's replies in Discord to show its files."}
    return {"status": "ready", "title": "Kronos mod post", "author": "", "files": files,
            "post_url": PostLink(active.guild, active.forum, active.thread, target.message).url}


def _discord_windows():
    from ctypes import wintypes
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process = kernel32.OpenProcess(0x1000, False, pid.value)
        if process:
            try:
                size = wintypes.DWORD(32768)
                path = ctypes.create_unicode_buffer(size.value)
                if kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(size)):
                    if os.path.basename(path.value).lower() in {"discord.exe", "discordptb.exe", "discordcanary.exe"}:
                        found.append(hwnd)
            finally:
                kernel32.CloseHandle(process)
        return True

    user32.EnumWindows.argtypes = [type(each), wintypes.LPARAM]
    user32.EnumWindows(each, 0)
    return found


def _legacy_forum(document, automation, U):
    """Confirm the current thread's parent from Discord's visible channel sidebar.

    Copy Message Link opens /guild/thread/message. That route omits the forum,
    even though the sidebar still puts the thread directly under its parent.
    Require both that parent link and the current thread title; merely having
    #mods somewhere in the server's channel list is not sufficient evidence.
    """
    title = document.GetCurrentPropertyValue(U.UIA_NamePropertyId)
    if not isinstance(title, str) or " | " not in title:
        return None
    title = title.rsplit(" | ", 1)[0].strip()
    if len(title) >= 2 and title[0] == title[-1] == '"':
        title = title[1:-1]
    if not title:
        return None
    walker = automation.ControlViewWalker
    links = document.FindAll(U.TreeScope_Descendants, automation.CreatePropertyCondition(
        U.UIA_ControlTypePropertyId, U.UIA_HyperlinkControlTypeId))
    found = set()
    for index in range(min(links.Length, 1000)):
        link = links.GetElement(index)
        try:
            route = None
            for prop in (U.UIA_ValueValuePropertyId, U.UIA_LegacyIAccessibleValuePropertyId):
                route = parse_post_link(link.GetCurrentPropertyValue(prop))
                if route:
                    break
            if not route or route.guild != GUILD_ID or route.forum not in FORUM_IDS or route.thread:
                continue
            item = walker.GetParentElement(link)
            for _ in range(5):
                if not item or item.GetCurrentPropertyValue(U.UIA_ControlTypePropertyId) == U.UIA_ListItemControlTypeId:
                    break
                item = walker.GetParentElement(item)
            if not item or item.GetCurrentPropertyValue(U.UIA_ControlTypePropertyId) != U.UIA_ListItemControlTypeId:
                continue
            following = walker.GetNextSiblingElement(item)
            if not following or following.GetCurrentPropertyValue(U.UIA_ControlTypePropertyId) != U.UIA_ListItemControlTypeId:
                continue
            buttons = following.FindAll(U.TreeScope_Descendants, automation.CreatePropertyCondition(
                U.UIA_ControlTypePropertyId, U.UIA_ButtonControlTypeId))
            for button_index in range(min(buttons.Length, 100)):
                name = buttons.GetElement(button_index).GetCurrentPropertyValue(U.UIA_NamePropertyId)
                if name == title or (isinstance(name, str) and name.startswith(title + " (") and name.endswith(")")):
                    found.add(route.forum)
        except Exception:
            continue
    return next(iter(found)) if len(found) == 1 else None


def read_snapshot(target: PostLink) -> dict:
    """One bounded, read-only scan. Must run in the dedicated helper process."""
    sys.coinit_flags = 0  # UI Automation clients run in an MTA, away from the GUI.
    import comtypes.client
    from comtypes.gen import UIAutomationClient as U

    automation = comtypes.client.CreateObject(U.CUIAutomation, interface=U.IUIAutomation)

    def value(element):
        for prop in (U.UIA_ValueValuePropertyId, U.UIA_LegacyIAccessibleValuePropertyId):
            try:
                text = element.GetCurrentPropertyValue(prop)
                if isinstance(text, str) and text:
                    return text
            except Exception:
                pass
        return ""

    for hwnd in _discord_windows():
        try:
            root = automation.ElementFromHandle(hwnd)
            document = root.FindFirst(U.TreeScope_Descendants, automation.CreatePropertyCondition(U.UIA_AutomationIdPropertyId, "RootWebArea"))
            if not document:
                continue
            url = value(document)
            active = parse_post_link(url)
            if not active or active.guild != GUILD_ID:
                continue
            if target.thread and active.thread != target.thread:
                continue
            if active.forum is None and active.thread:
                forum = _legacy_forum(document, automation, U)
                if forum:
                    active = PostLink(active.guild, forum, active.thread, active.message)
                    url = active.url
            if active.forum not in FORUM_IDS or (target.forum and active.forum != target.forum):
                continue
            if not active.thread:
                return {"url": url}
            if target.message:
                message = document.FindFirst(U.TreeScope_Descendants, automation.CreatePropertyCondition(
                    U.UIA_AutomationIdPropertyId, f"chat-messages-{active.thread}-{target.message}"))
                messages = [message] if message else []
            else:
                # Attachments are often published as updates in replies, not in the opening message.
                loaded = document.FindAll(U.TreeScope_Descendants, automation.CreatePropertyCondition(
                    U.UIA_ControlTypePropertyId, U.UIA_ListItemControlTypeId))
                messages = [loaded.GetElement(i) for i in range(min(loaded.Length, 1000))]
            result = []
            for message in messages:
                identity = message.GetCurrentPropertyValue(U.UIA_AutomationIdPropertyId)
                match = re.fullmatch(r"chat-messages-(\d{17,20})-(\d{17,20})", identity or "")
                if not match or match[1] != active.thread:
                    continue
                links = message.FindAll(U.TreeScope_Descendants, automation.CreatePropertyCondition(
                    U.UIA_ControlTypePropertyId, U.UIA_HyperlinkControlTypeId))
                files = []
                for i in range(min(links.Length, 100)):
                    item = attachment(value(links.GetElement(i)), allow_images=active.forum == ASSETS_FORUM_ID)
                    if item:
                        files.append(item)
                result.append({"thread_id": match[1], "message_id": match[2], "links": files})
            return {"url": url, "messages": result}
        except Exception:
            continue
    return {}


def helper_main(url, output):
    target = parse_post_link(url)
    if not target or target.guild != GUILD_ID:
        return 2
    # A child writes only its parent's designated temporary result file.
    parent = os.path.realpath(os.path.dirname(output))
    temp = os.path.realpath(tempfile.gettempdir())
    if (os.path.dirname(parent) != temp or not os.path.basename(parent).startswith("kp-discord-")
            or os.path.basename(output) != "snapshot.json"):
        return 2
    try:
        snapshot = read_snapshot(target)
    except Exception:
        snapshot = {"reader_error": "The Discord attachment reader could not start. Restart Kronos Plus and Discord, then try again."}
    with open(output, "w", encoding="utf-8") as file:
        json.dump(snapshot, file)
    return 0


class DesktopPostImporter:
    def __init__(self, opener, entry, timeout=120, runner=None):
        self._opener, self._entry, self._timeout = opener, entry, timeout
        self._runner = runner or self._capture
        self._lock = threading.RLock()
        self._jobs = {}

    def begin(self, url):
        target = parse_post_link(url)
        if not target or target.guild != GUILD_ID:
            raise ValueError("Copy a post link from the Kronos #mods or #assets forum.")
        self.close()
        job = {"cancel": threading.Event(), "process": None,
               "result": {"status": "waiting", "message": "Opening the post in your existing Discord window…"}}
        key = uuid.uuid4().hex
        with self._lock:
            self._jobs[key] = job
        try:
            self._opener(target.desktop_path)
        except OSError:
            self.cancel(key)
            raise ValueError("Open the Discord desktop app and sign in normally, then paste the post link again.")
        threading.Thread(target=self._watch, args=(job, target), daemon=True).start()
        return key

    def _capture(self, target, job):
        folder = tempfile.mkdtemp(prefix="kp-discord-")
        output = os.path.join(folder, "snapshot.json")
        command = ([sys.executable] if getattr(sys, "frozen", False) else [sys.executable, self._entry])
        command += ["--read-discord-post", target.url, output]
        process = None
        try:
            with self._lock:
                if job["cancel"].is_set():
                    return {}
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
                job["process"] = process
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()  # Only the child process this request created.
                process.wait()
                return {}
            if process.returncode == 0 and os.path.isfile(output):
                with open(output, encoding="utf-8") as file:
                    return json.load(file)
            return {"reader_error": "The Discord reader stopped unexpectedly. Restart the app and try again."}
        finally:
            with self._lock:
                if job.get("process") is process:
                    job["process"] = None
            # Remove exactly the helper's own output and empty temp directory.
            if os.path.isfile(output):
                os.remove(output)
            try:
                os.rmdir(folder)
            except OSError:
                pass

    def _watch(self, job, target):
        deadline = time.monotonic() + self._timeout
        while not job["cancel"].is_set() and time.monotonic() < deadline:
            try:
                snapshot = self._runner(target, job)
                if job["cancel"].is_set():
                    return
                if snapshot.get("reader_error"):
                    result = {"status": "error", "message": snapshot["reader_error"]}
                else:
                    result = select_snapshot(target, snapshot)
                with self._lock:
                    job["result"] = result
                if result["status"] in {"ready", "error"} or (result["status"] == "empty" and not result.get("waiting")):
                    return
            except Exception:
                with self._lock:
                    job["result"] = {"status": "waiting", "message": "Waiting for Discord to show the requested post…"}
            job["cancel"].wait(1)
        if not job["cancel"].is_set():
            with self._lock:
                job["result"] = {"status": "error", "message": "The post did not become readable in Discord. Open it in the desktop app, then try again."}

    def status(self, key):
        with self._lock:
            job = self._jobs.get(key)
            return dict(job["result"]) if job else {"status": "cancelled"}

    def cancel(self, key):
        with self._lock:
            job = self._jobs.pop(key, None)
            if job:
                job["cancel"].set()
                process = job.get("process")
                if process and process.poll() is None:
                    try:
                        process.kill()
                    except OSError:
                        pass

    def close(self):
        with self._lock:
            for key in list(self._jobs):
                self.cancel(key)
