"""Invoke Download on one verified attachment using Discord's normal accessibility UI.

No message actions, account data, or private API calls. Window-scoped clicks do
not move the user's cursor, and are verified against the exact UIA control.
The filename, message, thread and parent forum must all match the requested post.
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import tempfile
import time

from discord_posts import GUILD_ID, FORUM_IDS, SNOWFLAKE, _discord_windows, _legacy_forum, parse_post_link, preview_name


def last_input_tick():
    from ctypes import wintypes
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]
    info = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        raise ValueError("Windows couldn't verify that Discord is idle. Try the post again.")
    return info.dwTime


def value(element, U):
    for prop in (U.UIA_ValueValuePropertyId, U.UIA_LegacyIAccessibleValuePropertyId):
        try:
            result = element.GetCurrentPropertyValue(prop)
            if isinstance(result, str) and result:
                return result
        except Exception:
            pass
    return ""


def verified_route(document, target, automation, U):
    active = parse_post_link(value(document, U))
    if not active or active.guild != GUILD_ID or active.thread != target.thread:
        return None
    forum = active.forum or _legacy_forum(document, automation, U)
    if forum not in FORUM_IDS or (target.forum and target.forum != forum):
        return None
    return active


def invoke(element, U, allow_expand=False):
    if not element.GetCurrentPropertyValue(U.UIA_IsEnabledPropertyId):
        raise ValueError("Discord's attachment control is temporarily disabled. Try the post again.")
    patterns = [("UIA_InvokePatternId", "IUIAutomationInvokePattern", "Invoke"),
                ("UIA_LegacyIAccessiblePatternId", "IUIAutomationLegacyIAccessiblePattern", "DoDefaultAction")]
    if allow_expand:
        patterns.append(("UIA_ExpandCollapsePatternId", "IUIAutomationExpandCollapsePattern", "Expand"))
    for pattern_name, interface_name, action in patterns:
        pattern_id, interface = getattr(U, pattern_name, None), getattr(U, interface_name, None)
        if pattern_id is None or interface is None:
            continue
        try:
            unknown = element.GetCurrentPattern(pattern_id)
            if not unknown:
                continue
            pattern = unknown.QueryInterface(interface)
        except Exception:
            continue
        try:
            getattr(pattern, action)()
        except Exception:
            # Once an action has been issued its outcome is unknown; never invoke it twice.
            raise ValueError("Discord couldn't activate the attachment's download control. Retry the post link.") from None
        return
    raise ValueError("Discord didn't expose an accessible action for the attachment's download control.")


def window_click(element, hwnd, automation, U, input_tick, expected_input,
                 clock=time.monotonic, pause=time.sleep):
    """Send a click only to the Discord window at this exact accessible control."""
    from ctypes import wintypes
    if not element.GetCurrentPropertyValue(U.UIA_IsEnabledPropertyId):
        raise ValueError("Discord's attachment download control is disabled. Retry the post link.")
    user = ctypes.windll.user32
    user.GetForegroundWindow.restype = wintypes.HWND
    user.SetForegroundWindow.argtypes = [wintypes.HWND]
    user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user.GetAncestor.restype = wintypes.HWND
    user.WindowFromPoint.argtypes = [wintypes.POINT]
    user.WindowFromPoint.restype = wintypes.HWND
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user.SendMessageTimeoutW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                         wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
    user.SendMessageTimeoutW.restype = ctypes.c_ssize_t
    previous_dpi = None
    if hasattr(user, "SetThreadDpiAwarenessContext"):
        user.SetThreadDpiAwarenessContext.argtypes = [wintypes.HANDLE]
        user.SetThreadDpiAwarenessContext.restype = wintypes.HANDLE
        previous_dpi = user.SetThreadDpiAwarenessContext(wintypes.HANDLE(-4))
    try:
        if user.GetAncestor(user.GetForegroundWindow(), 2) != hwnd:
            user.SetForegroundWindow(hwnd)
        if user.GetAncestor(user.GetForegroundWindow(), 2) != hwnd or input_tick() != expected_input:
            raise ValueError("Discord isn't ready for the attachment download. Retry while leaving Discord idle briefly.")
        point, available = element.GetClickablePoint()
        if not available:
            # Chromium may still report an occluded control immediately after
            # Discord is raised. Focusing only this verified attachment button
            # also brings it into view when the message is taller than a screen.
            try:
                element.SetFocus()
            except Exception:
                pass
            deadline = clock() + 2
            while not available and clock() < deadline:
                if (input_tick() != expected_input
                        or user.GetAncestor(user.GetForegroundWindow(), 2) != hwnd):
                    raise ValueError("Discord received input before the download. Retry the post link.")
                pause(0.05)
                point, available = element.GetClickablePoint()
            if not available:
                raise ValueError("Discord couldn't bring the attachment's download control into view. Retry the post link.")
        hit = automation.ElementFromPoint(point)
        matches = False
        for _ in range(6):
            if not hit:
                break
            if automation.CompareElements(hit, element):
                matches = True
                break
            hit = automation.ControlViewWalker.GetParentElement(hit)
        if not matches:
            raise ValueError("The attachment control moved or is covered. Retry the post link.")
        screen = wintypes.POINT(point.x, point.y)
        receiver = user.WindowFromPoint(screen)
        if not receiver or user.GetAncestor(receiver, 2) != hwnd:
            raise ValueError("Another window is covering the Discord attachment.")
        expected_pid, actual_pid = wintypes.DWORD(), wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(expected_pid))
        user.GetWindowThreadProcessId(receiver, ctypes.byref(actual_pid))
        if not expected_pid.value or actual_pid.value != expected_pid.value:
            raise ValueError("The download control no longer belongs to Discord.")
        client = wintypes.POINT(point.x, point.y)
        if not user.ScreenToClient(receiver, ctypes.byref(client)) or not 0 <= client.x < 32768 or not 0 <= client.y < 32768:
            raise ValueError("Discord didn't expose a valid attachment click position.")
        position = (client.y << 16) | client.x
        if input_tick() != expected_input:
            raise ValueError("Discord received input before the download. Retry the post link.")
        for message, buttons in ((0x0200, 0), (0x0201, 1), (0x0202, 0)):
            result = ctypes.c_size_t()
            if not user.SendMessageTimeoutW(receiver, message, buttons, position, 2, 1000, ctypes.byref(result)):
                raise ValueError("Discord didn't respond to the attachment download control.")
    finally:
        if previous_dpi:
            user.SetThreadDpiAwarenessContext(previous_dpi)


def download_preview(target, message_id, name, automation=None, U=None, windows=None,
                     input_tick=last_input_tick, clock=time.monotonic, pause=time.sleep, activate=None):
    if (target.guild != GUILD_ID or not target.thread or not SNOWFLAKE.fullmatch(message_id or "")
            or (target.message and target.message != message_id) or preview_name(name) != name):
        raise ValueError("The requested Discord attachment is invalid.")
    if automation is None:
        sys.coinit_flags = 0
        import comtypes.client
        from comtypes.gen import UIAutomationClient as U
        automation = comtypes.client.CreateObject(U.CUIAutomation, interface=U.IUIAutomation)
    def find(root, prop, expected):
        return root.FindFirst(U.TreeScope_Descendants, automation.CreatePropertyCondition(prop, expected))
    for hwnd in _discord_windows() if windows is None else windows:
        root = automation.ElementFromHandle(hwnd)
        document = find(root, U.UIA_AutomationIdPropertyId, "RootWebArea")
        if not document or not verified_route(document, target, automation, U):
            continue
        message = find(document, U.UIA_AutomationIdPropertyId, f"chat-messages-{target.thread}-{message_id}")
        if not message:
            continue
        groups = message.FindAll(U.TreeScope_Descendants, automation.CreatePropertyCondition(
            U.UIA_NamePropertyId, "Plaintext file preview controls"))
        matches = []
        for index in range(min(groups.Length, 20)):
            group = groups.GetElement(index)
            texts = group.FindAll(U.TreeScope_Descendants, automation.CreatePropertyCondition(
                U.UIA_ControlTypePropertyId, U.UIA_TextControlTypeId))
            if any(texts.GetElement(i).GetCurrentPropertyValue(U.UIA_NamePropertyId) == name
                   for i in range(min(texts.Length, 100))):
                matches.append(group)
        if len(matches) != 1:
            continue
        # Do not act through a context menu that somebody else already opened.
        if find(document, U.UIA_ControlTypePropertyId, U.UIA_MenuControlTypeId):
            raise ValueError("Close the open menu in Discord, then retry the post link.")
        more = find(matches[0], U.UIA_NamePropertyId, "More")
        if not more or more.GetCurrentPropertyValue(U.UIA_ControlTypePropertyId) != U.UIA_ButtonControlTypeId:
            raise ValueError("Discord didn't expose the attachment's Download menu.")
        initial_input = input_tick()
        if activate is None:
            window_click(more, hwnd, automation, U, input_tick, initial_input)
        else:
            activate(more, U, True)
        deadline = clock() + 3
        while clock() < deadline:
            if input_tick() != initial_input:
                raise ValueError("Discord received input during the download. Retry the post while leaving Discord idle briefly.")
            if not verified_route(document, target, automation, U):
                raise ValueError("Discord changed posts before the attachment could be downloaded.")
            menu = find(document, U.UIA_AutomationIdPropertyId, "plaintext-preview-overflow-menu")
            if menu:
                button = find(menu, U.UIA_AutomationIdPropertyId, "plaintext-preview-overflow-menu-download")
                if button:
                    # Recheck the exact message and filename before the inbound download.
                    if not find(message, U.UIA_NamePropertyId, name):
                        raise ValueError("The attachment changed before it could be downloaded.")
                    if activate is None:
                        window_click(button, hwnd, automation, U, input_tick, initial_input)
                    else:
                        activate(button, U, False)
                    return {"status": "requested", "name": name}
            pause(0.05)
        raise ValueError("Discord's attachment Download menu did not open. Retry the post link.")
    raise ValueError("The requested attachment isn't loaded in Discord. Open that post and retry.")


def download_main(url, message_id, name, output):
    target = parse_post_link(url)
    parent, temp = os.path.realpath(os.path.dirname(output)), os.path.realpath(tempfile.gettempdir())
    if (not target or target.guild != GUILD_ID or os.path.dirname(parent) != temp
            or not os.path.basename(parent).startswith("kp-discord-") or os.path.basename(output) != "snapshot.json"):
        return 2
    try:
        result = download_preview(target, message_id, name)
    except Exception as error:
        result = {"status": "error", "message": str(error) if isinstance(error, ValueError) else
                  "Discord couldn't start the attachment download. Try the post again."}
    with open(output, "w", encoding="utf-8") as file:
        json.dump(result, file)
    return 0
