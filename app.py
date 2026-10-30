"""Kronos Plus - modern window (pywebview + HTML).

All the real work lives in kronos_qol.py; this file only exposes it to the
page in ui/index.html. If pywebview or WebView2 is missing, it falls back to
the classic window.
"""

import os
import shutil
import subprocess
import sys
import urllib.parse

# The accessibility reader is an isolated, read-only child, not another app window.
if len(sys.argv) == 4 and sys.argv[1] == "--read-discord-post":
    base = os.path.dirname(os.path.abspath(__file__))
    for candidate in (os.path.join(base, "vendor"), os.path.join(os.path.dirname(base), "vendor")):
        if os.path.isdir(candidate):
            sys.path.insert(0, candidate)
            break
    from discord_posts import helper_main
    raise SystemExit(helper_main(sys.argv[2], sys.argv[3]))

import kronos_qol as core
from discord_posts import DesktopPostImporter
from pack_services import PackServices, source_link

if getattr(sys, "frozen", False):
    # The windowed .exe has no console: without this, the first print or log line crashes it.
    # Anything printed goes to a log next to the app's state instead.
    sys.stdout = sys.stderr = open(os.path.join(core.DATA_DIR, "kronos_plus.log"), "w", encoding="utf-8", buffering=1)

    # Unzipping a download with Explorer marks every file as "from the internet", and .NET
    # then refuses to load our bundled DLLs (pythonnet, WebView2), so the full window can't start.
    # Clear that mark from our own DLLs only.
    for folder, _, files in os.walk(sys._MEIPASS):
        for name in files:
            if name.lower().endswith(".dll"):
                try:
                    os.remove(os.path.join(folder, name) + ":Zone.Identifier")
                except OSError:
                    pass

UI = os.path.join(core.APP_DIR, "ui", "index.html")
ICON = os.path.join(core.APP_DIR, "kronos_plus.ico")
TITLE = "Kronos Plus"
ASSETS_FORUM = "1564034358094864515/1564893868724588645"
MODS_FORUM = "1564034358094864515/1564893232985415700"  # Kronos Discord server / #mods forum


def set_window_icon():
    """Put the K+ icon on our window and taskbar button (WinForms otherwise shows Python's)."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    if not os.path.isfile(ICON):
        return
    # LR_LOADFROMFILE; IMAGE_ICON = 1; WM_SETICON = 0x80 with ICON_SMALL = 0 / ICON_BIG = 1
    small = user32.LoadImageW(None, ICON, 1, 16, 16, 0x10)
    big = user32.LoadImageW(None, ICON, 1, 32, 32, 0x10)
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        # Only our visible main window: hidden helper windows may never pump messages.
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid() and user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(64)
            user32.GetWindowTextW(hwnd, buf, 64)
            if buf.value == TITLE:
                found.append(hwnd)
        return True

    user32.EnumWindows(each, 0)
    for hwnd in found:
        # Post, don't send: never wait on the UI thread from here.
        user32.PostMessageW(hwnd, 0x80, 0, small)
        user32.PostMessageW(hwnd, 0x80, 1, big)


def clipboard_text():
    """(change counter, text) of the Windows clipboard; text is "" if it holds no text."""
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    seq = user32.GetClipboardSequenceNumber()
    if not user32.OpenClipboard(None):
        return seq, ""
    try:
        handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
        pointer = kernel32.GlobalLock(handle) if handle else None
        if not pointer:
            return seq, ""
        try:
            return seq, ctypes.wstring_at(pointer)[:2000]
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def open_discord(path):
    """Open discord.com/channels/<path> in the Discord app if it's installed, else in the browser."""
    try:
        os.startfile("discord://-/channels/" + path)
    except OSError:
        os.startfile("https://discord.com/channels/" + path)


class Api:
    def __init__(self):
        self._state = core.load_state()
        self._tracker = core.SessionTracker(self._state)
        self._window = None
        self._update = None
        self._updating = False
        self._post_importer = DesktopPostImporter(open_discord, os.path.abspath(__file__))
        self._packs = PackServices(core, self._state)

    # ---------------------------------------------------------- helpers

    def _dialog(self, kind, **kw):
        return self._window.create_file_dialog(kind, **kw)

    def _pack_services(self):
        if not hasattr(self, "_packs"):
            self._packs = PackServices(core, self._state)
        return self._packs

    def _pack_call(self, method, *args):
        import zipfile
        try:
            return method(*args)
        except (ValueError, OSError, zipfile.BadZipFile) as error:
            return {"error": str(error) or "The pack operation couldn't finish."}

    # ---------------------------------------------------------- overview

    def overview(self):
        s = self._state
        updated, last, build = core.steam_updated(s)
        mods = []
        for n, on, d in core.list_mods():
            man = core.load_manifest(n) or {}
            mods.append({"name": n, "enabled": on, "desc": d, "prepared": core.is_prepared(n),
                         "version": man.get("version", ""), "author": man.get("author", "")})
        banners = []
        if s.get("test_alone"):
            t = s["test_alone"]
            banners.append({"kind": "info", "action": "stop-test",
                            "text": f"Testing {t['mod']} alone. Your other mods come back when the game closes."})
        if updated:
            banners.append({"kind": "warn", "text": f"Steam updated BO7 (build {last} → {build}). Check the Kronos Discord before playing."})
        if s.get("safe_mode_saved") is not None:
            banners.append({"kind": "info", "text": "Safe mode is on — every mod is off."})
        if s.get("bisect"):
            b = s["bisect"]
            banners.append({"kind": "info", "text": f"Crash search round {b['round']}: testing {len(b['testing'])} of {len(b['suspects'])} suspects."})
        total = sum(x["minutes"] for x in s["sessions"])
        return {
            "mods": mods,
            "enabledCount": sum(m["enabled"] for m in mods),
            "gameDir": core.game_dir(),
            "modsForumUrl": "https://discord.com/channels/" + MODS_FORUM,
            "assetsForumUrl": "https://discord.com/channels/" + ASSETS_FORUM,
            "presets": sorted(s["presets"]),
            "presetMods": s["presets"],
            "banners": banners,
            "safeMode": s.get("safe_mode_saved") is not None,
            "bisect": s.get("bisect"),
            "history": list(reversed(s["history"])),
            "dark": s["dark"],
            "devMode": s["dev_mode"],
            "appVersion": core.APP_VERSION,
            "assetCount": len(core.list_assets()),
            "packCount": len(self._pack_services().snapshot()["packs"]),
            "testAlone": s.get("test_alone"),
            "playMinutes": total,
            "sessionCount": len(s["sessions"]),
            "templates": {k: {"label": v["param"][0], "default": v["param"][1]} for k, v in core.TEMPLATES.items()},
        }

    # ---------------------------------------------------------- updates

    def check_update(self):
        """{"status": "new", "version", "notes"} when a newer release is on GitHub, else "current" or "offline"."""
        try:
            self._update = core.latest_release()
        except ValueError as e:
            return {"status": "offline", "error": str(e)}
        if not self._update:
            return {"status": "current"}
        return {"status": "new", "version": self._update["version"], "notes": self._update["notes"]}

    def install_update(self):
        """Download the update, start it, and close this window so it can replace us. Returns an error or None."""
        if not self._update:
            return "No update is waiting."
        if not getattr(sys, "frozen", False):
            return "Only Kronos Plus.exe updates itself. Running from source? Use git pull."
        if self._tracker.current:
            return "Close the game first, then update."
        try:
            new_dir = core.download_update(self._update)
        except ValueError as e:
            return str(e)
        subprocess.Popen([os.path.join(new_dir, core.APP_EXE), "--finish-update",
                          os.path.dirname(sys.executable), str(os.getpid())], cwd=new_dir)
        self._updating = True
        self._window.destroy()
        return None

    def set_theme(self, dark):
        self._state["dark"] = bool(dark)
        core.save_state(self._state)

    # ---------------------------------------------------------- mods

    def set_mods(self, names, enabled):
        if not names:
            return
        core.record_history(self._state, f"Turned {'on' if enabled else 'off'} {', '.join(names)}")
        return self._pack_call(self._pack_services().manager.set_mods, names, enabled)

    def undo(self):
        if not self._state["history"]:
            return None
        previous = self._state["history"][-1]
        result = self._pack_call(self._pack_services().manager.set_all_mods, previous["before"])
        if isinstance(result, dict) and result.get("error"):
            return result
        self._state["history"].pop()
        core.save_state(self._state)
        return previous["action"]

    def delete_mod(self, name):
        """Returns an error message or None."""
        try:
            core.delete_mod(name)
        except ValueError as e:
            return str(e)
        return None

    def source(self, name):
        p = core.mod_path(name)
        if not p:
            return ""
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()

    def compile(self, names):
        names = names or core.enabled_mods()
        out = []
        for n in names:
            ok, msg = core.compile_check(n)
            out.append({"name": n, "ok": ok, "msg": msg})
        return out

    def open_mods_forum(self):
        open_discord(MODS_FORUM)

    def open_post(self, url):
        if core.is_post_link(url):
            open_discord(url.strip().split("/channels/", 1)[1])

    def clipboard_link(self, seen):
        """A Discord file link copied since change counter `seen`, as {"seq", "link"}.

        The page polls this while it waits for the user to Copy Link on a file in Discord.
        """
        seq, text = clipboard_text()
        text = text.strip()
        found = seq != seen and seen is not None and urllib.parse.urlsplit(text).hostname in core.LINK_HOSTS
        if found and self._window:
            # Pop back in front of Discord so the install steps are seen.
            self._window.restore()
            self._window.on_top = True
            self._window.on_top = False
        return {"seq": seq, "link": text if found else None}

    def pick_mod_files(self):
        import webview
        paths = self._dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=("GSC mods (*.gsc)",)) or []
        return [self._describe_file(p) for p in paths]

    def _describe_file(self, p):
        problem = core.check_mod_file(p)
        exists = os.path.exists(os.path.join(core.scripts_dir(), os.path.basename(p)))
        return {"path": p, "name": os.path.basename(p), "problem": problem, "exists": exists}

    def import_files(self, paths, overwrite):
        def install():
            plan = self._pack_services().prepare(paths)
            result = self._pack_services().install(plan["token"], overwrite, plan["name"])
            return [f"Added {path}." for path in result["installed"]]
        return self._pack_call(install)

    def prepare_files(self, paths):
        return self._pack_call(self._pack_services().prepare, paths)

    def link_mod(self, url, source_post=None, update_id=None):
        def resolve():
            if core.is_post_link(url):
                if core.POST_HELPER:
                    return dict(core.post_files(url), kind="choose")
                return {"kind": "post", "job": self._post_importer.begin(url)}
            return dict(self._pack_services().download([url], source_post, update_id), kind="pack")
        return self._pack_call(resolve)

    def link_files(self, urls, source_post=None, update_id=None):
        return self._pack_call(self._pack_services().download, urls, source_post, update_id)

    def revise_plan(self, token, folders):
        return self._pack_call(self._pack_services().revise, token, folders)

    def cancel_plan(self, token):
        self._pack_services().forget(token)

    def post_link_status(self, job):
        """Attachment discovery in the existing Discord window; no account token is read."""
        result = self._post_importer.status(job)
        if result.get("status") == "ready" and self._window:
            try:
                self._window.restore()
                self._window.on_top = True
                self._window.on_top = False
            except Exception:
                pass
        return result

    def cancel_post_link(self, job):
        self._post_importer.cancel(job)

    def forget_link(self, path):
        core.forget_download(path)

    def edit_mod(self, name):
        p = core.mod_path(name)
        if p:
            import subprocess
            subprocess.Popen(["notepad.exe", p])

    def open_scripts_folder(self):
        os.makedirs(core.scripts_dir(), exist_ok=True)
        os.startfile(core.scripts_dir())

    def open_assets_folder(self):
        os.makedirs(core.assets_dir(), exist_ok=True)
        os.startfile(core.assets_dir())

    # ---------------------------------------------------------- assets

    def assets(self):
        return self._pack_services().assets()

    def asset_thumbs(self, rels):
        return core.asset_thumbs(list(rels or []))

    def asset_preview(self, rel):
        try:
            return core.asset_preview(rel)
        except (ValueError, OSError) as e:
            return {"error": str(e)}

    def show_asset(self, rel):
        try:
            subprocess.Popen(["explorer", "/select,", core.asset_file(rel)])
        except (ValueError, OSError):
            pass

    def delete_asset(self, rel):
        """Returns an error message or None."""
        try:
            core.delete_asset(rel, self._state)
        except (ValueError, OSError) as e:
            return str(e)
        return None

    # ---------------------------------------------------------- presets

    def save_preset(self, name):
        name = (name or "").strip()
        if not name:
            return False
        self._state["presets"][name] = core.enabled_mods()
        core.save_state(self._state)
        return True

    def apply_preset(self, name):
        if name in self._state["presets"]:
            core.record_history(self._state, f"Applied preset {name}")
            return self._pack_call(self._pack_services().manager.set_all_mods, self._state["presets"][name])

    def delete_preset(self, name):
        self._state["presets"].pop(name, None)
        core.save_state(self._state)

    # ---------------------------------------------------------- packs

    def export_pack(self):
        import webview
        p = self._dialog(webview.SAVE_DIALOG, save_filename="my_kronos_mods.zip", file_types=("Mod pack (*.zip)",))
        if not p:
            return None
        p = p if isinstance(p, str) else p[0]
        if not p.lower().endswith(".zip"):
            p += ".zip"
        inc, skip = core.export_pack(p, os.path.splitext(os.path.basename(p))[0])
        return {"file": os.path.basename(p), "included": inc, "skipped": skip}

    def pick_pack(self):
        import webview
        paths = self._dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=("Mods and assets (*.zip;*.gsc;*.lua;*.png;*.jpg;*.jpeg;*.dds;*.tga;*.bmp;*.webp;*.csv;*.tsv;*.json;*.txt;*.cfg;*.ini;*.xml;*.raw;*.bin;*.csc;*.ents;*.mapents)",))
        return self.prepare_files(list(paths)) if paths else None

    def _describe_pack(self, path, asset_folder=None):
        return self._pack_services().prepare([path], {"0": asset_folder} if asset_folder else None)

    def preview_asset(self, token, folder):
        return self.revise_plan(token, {"0": folder})

    def install_pack(self, token, overwrite, make_preset=False, name=None):
        return self._pack_call(self._pack_services().install, token, overwrite, name, make_preset)

    def managed_packs(self):
        return self._pack_call(self._pack_services().snapshot)

    def pack_action_preview(self, identity, action):
        return self._pack_call(self._pack_services().action_preview, identity, action)

    def pack_action(self, identity, action):
        return self._pack_call(self._pack_services().manager.change, identity, action)

    def pack_source(self, identity, url):
        def save():
            self._pack_services().manager.set_source(identity, source_link(url))
            return {"saved": True}
        return self._pack_call(save)

    def save_full_profile(self, name):
        return self._pack_call(self._pack_services().manager.save_profile, name)

    def apply_full_profile(self, name):
        return self._pack_call(self._pack_services().manager.apply_profile, name)

    def delete_full_profile(self, name):
        def remove():
            self._pack_services().manager.delete_profile(name)
            return {"deleted": True}
        return self._pack_call(remove)

    # ---------------------------------------------------------- troubleshoot

    def safe_mode(self, on):
        if on and self._state.get("test_alone"):
            return "Stop testing your mod first."
        if on and self._state.get("safe_mode_saved") is None:
            core.record_history(self._state, "Safe mode on")
            core.safe_mode_on(self._state)
        elif not on:
            core.safe_mode_off(self._state)

    def bisect_start(self):
        return core.bisect_start(self._state)

    def bisect_answer(self, crashed):
        if not self._state.get("bisect"):
            return None
        return core.bisect_answer(self._state, crashed)

    def bisect_cancel(self):
        core.bisect_cancel(self._state)

    # ---------------------------------------------------------- sessions

    def poll_session(self):
        r = self._tracker.poll()
        if r == "ended" and self._state.get("test_alone"):
            core.test_alone_stop(self._state)
            return "ended-test"
        return r

    def sessions(self):
        s = self._state["sessions"]
        sus = core.crash_suspects(self._state)
        return {
            "sessions": list(reversed(s)),
            "suspects": [{"name": m, "rate": r, "count": t} for m, r, t in sus[:5]],
            "minutes": sum(x["minutes"] for x in s),
            "crashes": sum(1 for x in s if x["crash"]),
        }

    # ---------------------------------------------------------- settings

    def settings(self):
        try:
            data = core.load_settings()
        except (OSError, ValueError) as e:
            return {"error": f"Couldn't read settings.json: {e}"}
        flags = []
        for label, path, invert in core.SETTING_FLAGS:
            val = bool(core.get_path(data, path, False))
            flags.append({"label": label, "key": ".".join(path), "value": (not val) if invert else val})
        texts = [{"label": label, "key": ".".join(path), "value": str(core.get_path(data, path, ""))}
                 for label, path in core.SETTING_TEXTS]
        return {"flags": flags, "texts": texts, "backups": core.list_backups()}

    def save_settings(self, values):
        data = core.load_settings()
        inverted = {".".join(p): inv for _, p, inv in core.SETTING_FLAGS}
        for key, val in values.items():
            path = tuple(key.split("."))
            if key in inverted:
                val = (not val) if inverted[key] else bool(val)
            core.set_path(data, path, val)
        core.save_settings(data)
        return True

    def restore_backup(self, name):
        core.restore_settings(name)
        return True

    # ---------------------------------------------------------- logs

    def logs(self):
        return [{"path": p, "name": os.path.basename(p)} for p in core.list_logs()]

    def read_log(self, path):
        if os.path.normcase(path) not in {os.path.normcase(p) for p in core.list_logs()}:
            return []
        return [{"text": line, "hit": bool(core.LOG_HIGHLIGHT.search(line))}
                for line in core.read_log(path).splitlines()]

    # ---------------------------------------------------------- studio (dev mode)

    def set_dev_mode(self, on):
        self._state["dev_mode"] = bool(on)
        core.save_state(self._state)

    def studio(self):
        out = []
        for n, on, _ in core.list_mods():
            if core.is_prepared(n):
                continue
            man = core.load_manifest(n) or {}
            issues = core.lint_mod(n)
            out.append({"name": n, "enabled": on, "title": man.get("title", n), "version": man.get("version", ""),
                        "errors": sum(i["severity"] == "error" for i in issues),
                        "warnings": sum(i["severity"] == "warning" for i in issues)})
        return out

    def project(self, name):
        man = core.load_manifest(name)
        return {
            "name": name,
            "enabled": name in core.enabled_mods(),
            "manifest": man or core.default_manifest(name),
            "hasManifest": man is not None,
            "source": self.source(name),
            "mtime": core.mod_mtime(name),
            "issues": core.lint_mod(name),
            "others": [n for n, _, _ in core.list_mods() if n != name],
            "vscode": core.editor_exe() is not None,
        }

    def project_defaults(self):
        return core.default_manifest("")

    def check_project(self, name):
        ok, msg = core.compile_check(name)
        line, text = core.compile_error_line(msg) if ok is False else (None, msg)
        return {"issues": core.lint_mod(name), "compile": {"ok": ok, "msg": msg, "line": line, "text": text}}

    def save_manifest(self, name, data):
        try:
            return {"manifest": core.save_manifest(name, data)}
        except (OSError, ValueError) as e:
            return {"error": str(e)}

    def create_project(self, name, manifest, template, n):
        name = (name or "").strip()
        try:
            core.record_history(self._state, f"Created {name}")
            core.create_project(name, manifest, template or None, n)
        except (ValueError, KeyError) as e:
            self._state["history"].pop()
            core.save_state(self._state)
            return {"ok": False, "error": str(e) or "Enter a whole number."}
        ok, msg = core.compile_check(name)
        return {"ok": True, "compiles": ok, "msg": msg}

    def save_source(self, name, code):
        try:
            return {"mtime": core.save_mod_source(name, code)}
        except (OSError, ValueError) as e:
            return {"error": str(e)}

    def lint_text(self, code):
        return core.lint_source(code)

    def mod_mtime(self, name):
        return core.mod_mtime(name)

    def completions(self):
        return core.completion_words()

    def console_poll(self, cursor):
        rows, cursor = core.console_read(cursor)
        return {"rows": rows, "cursor": cursor, "files": [os.path.basename(p) for p in core.console_files()]}

    def test_alone(self, name):
        return core.test_alone_start(self._state, name)

    def stop_test(self):
        core.test_alone_stop(self._state)

    def open_in_editor(self, name):
        p = core.mod_path(name)
        if not p:
            return None
        import subprocess
        exe = core.editor_exe()
        subprocess.Popen([exe, p] if exe else ["notepad.exe", p])
        return "VS Code" if exe else "Notepad"

    # ---------------------------------------------------------- health / launch

    def health(self):
        return [{"ok": ok, "title": t, "detail": d} for ok, t, d in core.health_checks(self._state)]

    def mark_update_handled(self):
        self._state["last_buildid"] = core.steam_buildid()
        core.save_state(self._state)

    def prelaunch(self):
        return core.prelaunch_problems(self._state)

    def launch(self):
        launcher = core.launcher_path(self._state)
        if not launcher:
            import webview
            picked = self._dialog(webview.OPEN_DIALOG, file_types=("Kronos launcher (KronosLauncher.exe)",))
            if not picked:
                return "Couldn't find KronosLauncher.exe. Pick it to play from here."
            launcher = picked[0] if isinstance(picked, (list, tuple)) else picked
            self._state["launcher"] = launcher
            core.save_state(self._state)
        os.startfile(launcher)
        return None


WEBVIEW2_KEY = r"Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
WEBVIEW2_PAGE = "https://developer.microsoft.com/microsoft-edge/webview2/"


def webview2_installed():
    """True when Microsoft Edge WebView2 Runtime is installed (machine-wide or for this user)."""
    import winreg
    for hive, path in ((winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\" + WEBVIEW2_KEY),
                       (winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\" + WEBVIEW2_KEY),
                       (winreg.HKEY_CURRENT_USER, "Software\\" + WEBVIEW2_KEY)):
        version = core.read_reg(path, "pv", hive)
        if version and version != "0.0.0.0":
            return True
    return False


def classic(missing_webview2=False):
    """Open the classic window, telling the user why the full one couldn't start."""
    import traceback
    traceback.print_exc()  # in the .exe this lands in kronos_plus.log
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    if missing_webview2:
        if messagebox.askyesno(
                TITLE, "Kronos Plus needs Microsoft Edge WebView2 for its full window, "
                "and it isn't installed on this PC.\n\nIt's free from Microsoft. Open the download page?\n\n"
                "The classic window opens either way. Restart Kronos Plus after installing."):
            os.startfile(WEBVIEW2_PAGE)
    else:
        messagebox.showwarning(
            TITLE, "The full window couldn't start, so Kronos Plus opened its classic window.\n\n"
            "Details are in " + os.path.join(core.DATA_DIR, "kronos_plus.log"))
    root.destroy()
    core.run_ui()


def finish_update(install_dir, pid):
    """Run by the new version from its download folder: wait for the old app to close, swap it in, reopen it."""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
    if handle:
        kernel32.WaitForSingleObject(handle, 60000)
        kernel32.CloseHandle(handle)
    try:
        core.replace_app(os.path.dirname(sys.executable), install_dir)
    except (OSError, ValueError) as e:
        print("Update failed:", repr(e))
        ctypes.windll.user32.MessageBoxW(
            None, f"Kronos Plus couldn't update, so your current version stays.\n\n{e}\n\n"
            "You can download the new version from GitHub instead.", TITLE, 0x30)
    subprocess.Popen([os.path.join(install_dir, core.APP_EXE)], cwd=install_dir)


def after_update():
    """On a normal start of the .exe: delete what the last update left behind."""
    here = os.path.dirname(sys.executable)
    if not os.path.realpath(here).startswith(os.path.realpath(core.UPDATE_DIR)):
        shutil.rmtree(core.UPDATE_DIR, ignore_errors=True)
        core.clean_old_app(here)


def main():
    if "--finish-update" in sys.argv:
        i = sys.argv.index("--finish-update")
        finish_update(sys.argv[i + 1], int(sys.argv[i + 2]))
        return
    if getattr(sys, "frozen", False):
        after_update()
    if not webview2_installed():
        classic(missing_webview2=True)
        return
    try:
        import webview
    except Exception:
        classic()
        return
    try:
        # Own taskbar group, so Windows shows our icon instead of Python's.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Kronos.KronosPlus")
    except (OSError, AttributeError):
        pass
    api = Api()
    window = webview.create_window(
        TITLE, UI, js_api=api, width=1240, height=800, min_size=(980, 640),
        background_color="#0f1115",
    )
    window.events.shown += set_window_icon
    window.events.closed += api._post_importer.close
    window.events.closed += api._pack_services().close
    api._window = window  # private: pywebview would otherwise crawl the whole window object
    try:
        webview.start(gui="edgechromium", debug="--debug" in sys.argv)
    except Exception:
        classic()
    if api._updating:
        os._exit(0)  # the new version is waiting for this process to end; don't let a stray thread hold it


if __name__ == "__main__":
    main()
