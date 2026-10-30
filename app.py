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

# Accessibility helpers are isolated children, not additional app windows.
if ((len(sys.argv) == 4 and sys.argv[1] == "--read-discord-post")
        or (len(sys.argv) == 6 and sys.argv[1] == "--download-discord-preview")):
    base = os.path.dirname(os.path.abspath(__file__))
    for candidate in (os.path.join(base, "vendor"), os.path.join(os.path.dirname(base), "vendor")):
        if os.path.isdir(candidate):
            sys.path.insert(0, candidate)
            break
    if sys.argv[1] == "--read-discord-post":
        from discord_posts import helper_main
        raise SystemExit(helper_main(sys.argv[2], sys.argv[3]))
    from discord_preview_download import download_main
    raise SystemExit(download_main(*sys.argv[2:]))

import kronos_qol as core
from discord_posts import DesktopPostImporter
from pack_services import PackServices, source_link
from post_downloads import AutomaticPostDownloads

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
# Folders shown in Settings: key -> (label, where, note). Kronos's launcher decides the first three.
FOLDERS = {
    "mods": ("Mods", core.scripts_dir, "Mods that are on. Change it with the Kronos launcher's Scripts folder setting."),
    "disabled": ("Turned-off mods", core.disabled_dir, "Kronos Plus moves mods here when you turn them off."),
    "assets": ("Assets", core.assets_dir, "Images, Lua and other files Kronos loads."),
    "game": ("Game", core.game_dir, "Your Kronos copy of BO7. Change it in the Kronos launcher."),
    "backups": ("Kronos Plus backups", lambda: core.BACKUP_DIR, "Settings backups, and the automatic backup made before a restore."),
}


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


def focus_window(pids):
    """Bring a visible window of one of these processes to the front (restoring it if minimized).
    True if there was one."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(each, 0)
    for hwnd in found[:1]:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
    return bool(found)


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


def set_clipboard_text(text):
    """Put text on the Windows clipboard; False if another program is holding it."""
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalLock.argtypes = kernel32.GlobalUnlock.argtypes = kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    data = ctypes.create_unicode_buffer(text)
    handle = kernel32.GlobalAlloc(0x0002, ctypes.sizeof(data))  # GMEM_MOVEABLE
    pointer = kernel32.GlobalLock(handle) if handle else None
    if not pointer:
        return False
    ctypes.memmove(pointer, data, ctypes.sizeof(data))
    kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        return False
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(13, handle):  # CF_UNICODETEXT; Windows owns the memory once this works
            kernel32.GlobalFree(handle)
            return False
        return True
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
        self._post_importer = DesktopPostImporter(open_discord, os.path.abspath(__file__), on_discovered=self._single_post_attachment)
        self._packs = PackServices(core, self._state)

    # ---------------------------------------------------------- helpers

    def _dialog(self, kind, **kw):
        return self._window.create_file_dialog(kind, **kw)

    def _pack_services(self):
        if not hasattr(self, "_packs"):
            self._packs = PackServices(core, self._state)
        return self._packs

    def _automatic_posts(self):
        if not hasattr(self, "_auto_posts"):
            self._auto_posts = AutomaticPostDownloads(self._post_importer, self._pack_services(), on_ready=self._show_import)
        return self._auto_posts

    def _single_post_attachment(self, job, update_id=None):
        # Run independently of WebView timers while Discord covers the main app.
        post = self._post_importer.status(job)
        if len(post.get("files", [])) + len(post.get("previews", [])) == 1:
            self._automatic_posts().start(job, [0], update_id)
        else:
            self._show_import()

    def _show_import(self):
        if getattr(self, "_window", None):
            try:
                self._window.restore()
                self._window.on_top = True
                self._window.on_top = False
            except Exception:
                pass

    def _resolve_restored(self):
        """Turn Kronos's own mods back off after its launcher put them back (see core.resolve_restored_mods)."""
        try:
            managed = self._pack_services().snapshot()["managed_paths"]
        except (ValueError, OSError):
            return []
        packed = {p[:-4] for p in managed if core.is_source_mod(p)}
        return core.resolve_restored_mods(packed)

    def _pack_call(self, method, *args):
        import zipfile
        self._resolve_restored()
        try:
            return method(*args)
        except (ValueError, OSError, zipfile.BadZipFile) as error:
            return {"error": str(error) or "The pack operation couldn't finish."}

    # ---------------------------------------------------------- overview

    def overview(self):
        s = self._state
        self._resolve_restored()
        updated, last, build = core.steam_updated(s)
        mods = []
        bundled = core.kronos_mods()
        for n, on, d in core.list_mods():
            man = core.load_manifest(n) or {}
            mods.append({"name": n, "title": s["names"].get(n, ""), "enabled": on, "desc": d, "prepared": core.is_prepared(n),
                         "kronos": n in bundled,
                         "version": man.get("version", ""), "author": man.get("author", "")})
        banners = []
        if s.get("test_alone"):
            t = s["test_alone"]
            banners.append({"kind": "info", "action": "stop-test",
                            "text": f"Testing {t['mod']} alone. Your other mods come back when the game closes."})
        if updated:
            banners.append({"kind": "warn", "text": f"Steam updated BO7 (build {last} → {build}). Check the Kronos Discord before playing."})
        if s.get("safe_mode_saved") is not None:
            banners.append({"kind": "info", "text": "Safe mode is on, so every mod is off."})
        if s.get("bisect"):
            b = s["bisect"]
            banners.append({"kind": "info", "text": f"Crash search round {b['round']}: testing {len(b['testing'])} of {len(b['suspects'])} suspects."})
        total = sum(x["minutes"] for x in s["sessions"])
        return {
            "mods": mods,
            "enabledCount": sum(m["enabled"] for m in mods),
            "gameDir": core.game_dir(),
            "folders": [{"key": k, "label": label, "path": path(), "note": note} for k, (label, path, note) in FOLDERS.items()],
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
        # The new version shows these once it opens.
        self._state["update_notes"] = {"version": self._update["version"], "notes": self._update["notes"]}
        core.save_state(self._state)
        subprocess.Popen([os.path.join(new_dir, core.APP_EXE), "--finish-update",
                          os.path.dirname(sys.executable), str(os.getpid())], cwd=new_dir)
        self._updating = True
        self._window.destroy()
        return None

    def whats_new(self):
        return core.whats_new(self._state)

    def open_release_page(self):
        os.startfile(core.RELEASE_PAGE.format(core.APP_VERSION))

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
        if self._state["names"].pop(name, None) is not None:
            core.save_state(self._state)
        return None

    def rename_mod(self, name, title):
        """{"title"} (None means it shows its file name again) or {"error"}."""
        try:
            return {"title": core.rename_mod(self._state, name, title)}
        except (ValueError, OSError) as e:
            return {"error": str(e)}

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

    def prepare_clipboard_files(self):
        def prepare():
            from clipboard_import import copied_files
            paths = copied_files()
            return self._pack_services().prepare(paths) if paths else None
        return self._pack_call(prepare)

    def link_mod(self, url, source_post=None, update_id=None):
        def resolve():
            if core.is_post_link(url):
                if core.POST_HELPER:
                    return dict(core.post_files(url), kind="choose")
                return {"kind": "post", "job": self._post_importer.begin(url, update_id=update_id)}
            return dict(self._pack_services().download([url], source_post, update_id), kind="pack")
        return self._pack_call(resolve)

    def link_files(self, urls, source_post=None, update_id=None):
        return self._pack_call(self._pack_services().download, urls, source_post, update_id)

    def revise_plan(self, token, folders):
        return self._pack_call(self._pack_services().revise, token, folders)

    def cancel_plan(self, token):
        self._pack_services().forget(token)

    def post_link_status(self, job, update_id=None):
        """Attachment discovery in the existing Discord window; no account token is read."""
        result = self._automatic_posts().status(job) or self._post_importer.status(job)
        if result.get("status") in {"ready", "downloaded"} and getattr(self, "_window", None):
            try:
                self._window.restore()
                self._window.on_top = True
                self._window.on_top = False
            except Exception:
                pass
        return result

    def select_post_attachments(self, job, indices, update_id=None):
        return self._pack_call(self._automatic_posts().start, job, indices, update_id)

    def cancel_post_link(self, job):
        self._automatic_posts().cancel(job)
        self._post_importer.cancel(job)
        self._pack_services().cancel_preview(job)

    def pick_preview_download(self, job, update_id=None):
        import webview
        post = self._post_importer.status(job)
        if not post.get("previews"):
            return {"error": "Open the Discord post again before choosing its preview file."}
        paths = self._dialog(webview.OPEN_DIALOG, allow_multiple=True,
            file_types=("Mods and assets (*.gsc;*.lua;*.txt;*.json;*.csv;*.tsv;*.cfg;*.ini;*.xml;*.csc;*.ents;*.mapents;*.zip;*.7z;*.rar)",))
        if not paths:
            return None
        if self._automatic_posts().status(job):
            return self._pack_call(self._automatic_posts().manual, job, list(paths))
        return self._pack_call(self._pack_services().prepare_preview, list(paths), post, update_id)

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

    def open_folder(self, key):
        if key in FOLDERS:
            path = FOLDERS[key][1]()
            os.makedirs(path, exist_ok=True)
            os.startfile(path)

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
        paths = self._dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=("Mods and assets (*.zip;*.7z;*.rar;*.gsc;*.lua;*.png;*.jpg;*.jpeg;*.dds;*.tga;*.bmp;*.webp;*.csv;*.tsv;*.json;*.txt;*.cfg;*.ini;*.xml;*.raw;*.bin;*.csc;*.ents;*.mapents)",))
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
        self._resolve_restored()
        if on and self._state.get("test_alone"):
            return "Stop testing your mod first."
        if on and self._state.get("safe_mode_saved") is None:
            core.record_history(self._state, "Safe mode on")
            core.safe_mode_on(self._state)
        elif not on:
            core.safe_mode_off(self._state)

    def bisect_start(self):
        self._resolve_restored()
        return core.bisect_start(self._state)

    def bisect_answer(self, crashed):
        if not self._state.get("bisect"):
            return None
        self._resolve_restored()
        return core.bisect_answer(self._state, crashed)

    def bisect_cancel(self):
        core.bisect_cancel(self._state)

    def help_report(self):
        try:
            return {"text": core.help_report(self._state, self._pack_services().snapshot()["packs"])}
        except (ValueError, OSError) as e:
            return {"error": f"Couldn't make the report: {e}"}

    def copy_help_report(self):
        report = self.help_report()
        if "error" in report:
            return report
        if not set_clipboard_text(report["text"]):
            return {"error": "Couldn't copy. Another program is using the clipboard, try again."}
        return {"chars": len(report["text"])}

    # ---------------------------------------------------------- full backups

    def backup_setup(self):
        import datetime
        import webview
        p = self._dialog(webview.SAVE_DIALOG, save_filename=f"Kronos Plus backup {datetime.date.today()}.zip",
                         file_types=("Kronos Plus backup (*.zip)",))
        if not p:
            return None
        p = p if isinstance(p, str) else p[0]
        if not p.lower().endswith(".zip"):
            p += ".zip"
        try:
            return {"file": os.path.basename(p), **core.create_setup_backup(p, self._state)}
        except (ValueError, OSError) as e:
            return {"error": f"Couldn't make the backup: {e}"}

    def pick_setup_backup(self):
        """Choose a backup to restore and say what's in it; restore_setup then restores that file."""
        import webview
        picked = self._dialog(webview.OPEN_DIALOG, file_types=("Kronos Plus backup (*.zip)",))
        if not picked:
            return None
        path = picked if isinstance(picked, str) else picked[0]
        try:
            info = core.read_setup_backup(path)
        except ValueError as e:
            return {"error": str(e)}
        self._restore_path = path
        return {"file": os.path.basename(path), **info}

    def restore_setup(self):
        path = getattr(self, "_restore_path", None)
        if not path:
            return {"error": "Choose a backup first."}
        if self._tracker.current or "cod25-cod.exe" in core.running_processes():
            return {"error": "Close the game first, then restore."}
        if self._state.get("test_alone") or self._state.get("bisect"):
            return {"error": "Finish testing or the crash search first, then restore."}
        try:
            core.restore_setup_backup(path, self._state)
        except (ValueError, OSError) as e:
            return {"error": str(e)}
        self._restore_path = None
        self._pack_services().close()  # install reviews made before the restore no longer fit
        return {"ok": True}

    # ---------------------------------------------------------- sessions

    def poll_session(self):
        """"idle" | "playing" | "ended" | "ended-test", or {"state", "fixed"} when Kronos mods the launcher
        put back were turned off again."""
        r = self._tracker.poll()
        if r == "ended" and self._state.get("test_alone"):
            core.test_alone_stop(self._state)
            r = "ended-test"
        fixed = self._resolve_restored() if "kronoslauncher.exe" in core.running_processes() else []
        return {"state": r, "fixed": fixed} if fixed else r

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
        self._resolve_restored()
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
        if "cod25-cod.exe" in core.running_processes():
            return []  # nothing to check: launch() says the game is already running
        return core.prelaunch_problems(self._state)

    def launch(self):
        """Open Kronos's launcher, where the game is started. {"status": "playing" | "shown" | "opened"} or {"error"}.

        Starting the launcher while it's already open does nothing visible, so an open one is brought to the front."""
        procs = core.running_processes()
        if "cod25-cod.exe" in procs:
            return {"status": "playing"}
        if "kronoslauncher.exe" in procs and focus_window(core.process_ids("kronoslauncher.exe")):
            return {"status": "shown"}
        launcher = core.launcher_path(self._state)
        if not launcher:
            import webview
            picked = self._dialog(webview.OPEN_DIALOG, file_types=("Kronos launcher (KronosLauncher.exe)",))
            if not picked:
                return {"error": "Couldn't find KronosLauncher.exe. Pick it to play from here."}
            launcher = picked[0] if isinstance(picked, (list, tuple)) else picked
            self._state["launcher"] = launcher
            core.save_state(self._state)
        try:
            os.startfile(launcher)
        except OSError as e:
            if getattr(e, "winerror", None) == 1223:  # the user said No to Windows' permission prompt
                return {"error": "The Kronos launcher needs your OK to start. Click Play again and choose Yes."}
            return {"error": f"Couldn't start the Kronos launcher: {e.strerror or e}"}
        return {"status": "opened"}


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
    window.events.closed += api._automatic_posts().close
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
