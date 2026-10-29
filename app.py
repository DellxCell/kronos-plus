"""Kronos Plus - modern window (pywebview + HTML).

All the real work lives in kronos_qol.py; this file only exposes it to the
page in ui/index.html. If pywebview or WebView2 is missing, it falls back to
the classic window.
"""

import os
import sys

import kronos_qol as core

if getattr(sys, "frozen", False):
    # The windowed .exe has no console: without this, the first print or log line crashes it.
    # Anything printed goes to a log next to the app's state instead.
    sys.stdout = sys.stderr = open(os.path.join(core.DATA_DIR, "kronos_plus.log"), "w", encoding="utf-8", buffering=1)

UI = os.path.join(core.APP_DIR, "ui", "index.html")
ICON = os.path.join(core.APP_DIR, "kronos_plus.ico")
TITLE = "Kronos Plus"


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


class Api:
    def __init__(self):
        self._state = core.load_state()
        self._tracker = core.SessionTracker(self._state)
        self._window = None

    # ---------------------------------------------------------- helpers

    def _dialog(self, kind, **kw):
        return self._window.create_file_dialog(kind, **kw)

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
            "presets": sorted(s["presets"]),
            "presetMods": s["presets"],
            "banners": banners,
            "safeMode": s.get("safe_mode_saved") is not None,
            "bisect": s.get("bisect"),
            "history": list(reversed(s["history"])),
            "dark": s["dark"],
            "devMode": s["dev_mode"],
            "testAlone": s.get("test_alone"),
            "playMinutes": total,
            "sessionCount": len(s["sessions"]),
            "templates": {k: {"label": v["param"][0], "default": v["param"][1]} for k, v in core.TEMPLATES.items()},
        }

    def set_theme(self, dark):
        self._state["dark"] = bool(dark)
        core.save_state(self._state)

    # ---------------------------------------------------------- mods

    def set_mods(self, names, enabled):
        if not names:
            return
        core.record_history(self._state, f"Turned {'on' if enabled else 'off'} {', '.join(names)}")
        for n in names:
            core.set_mod_enabled(n, enabled)

    def undo(self):
        return core.undo_last(self._state)

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

    def create_from_template(self, template, name, n):
        try:
            core.record_history(self._state, f"Created {name}")
            core.make_from_template(template, name.strip(), int(n))
        except ValueError as e:
            self._state["history"].pop()
            core.save_state(self._state)
            return {"ok": False, "error": str(e) or "Enter a whole number."}
        ok, msg = core.compile_check(name.strip())
        return {"ok": True, "compiles": ok, "msg": msg}

    def pick_mod_files(self):
        import webview
        paths = self._dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=("GSC mods (*.gsc)",)) or []
        result = []
        for p in paths:
            problem = core.check_mod_file(p)
            exists = os.path.exists(os.path.join(core.scripts_dir(), os.path.basename(p)))
            result.append({"path": p, "name": os.path.basename(p), "problem": problem, "exists": exists})
        return result

    def import_files(self, paths, overwrite):
        core.record_history(self._state, "Added mods")
        msgs = []
        for p in paths:
            ok, msg = core.import_mod(p, overwrite=os.path.basename(p) in overwrite)
            msgs.append(msg if ok else f"{os.path.basename(p)}: {'skipped (already exists)' if msg == 'exists' else msg}")
        return msgs

    def edit_mod(self, name):
        p = core.mod_path(name)
        if p:
            import subprocess
            subprocess.Popen(["notepad.exe", p])

    def open_scripts_folder(self):
        os.makedirs(core.scripts_dir(), exist_ok=True)
        os.startfile(core.scripts_dir())

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
            core.apply_enabled_set(self._state["presets"][name])

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
        import zipfile
        paths = self._dialog(webview.OPEN_DIALOG, file_types=("Mod pack (*.zip)",))
        if not paths:
            return None
        p = paths[0]
        try:
            name, files, bad = core.read_pack(p)
        except zipfile.BadZipFile:
            return {"error": "That isn't a valid .zip file."}
        existing = [b for b in files if os.path.exists(os.path.join(core.scripts_dir(), b))]
        mods = sorted(b for b in files if b.lower().endswith(".gsc"))
        return {"path": p, "name": name, "files": mods, "bad": bad, "existing": existing}

    def install_pack(self, path, overwrite, make_preset):
        name, files, bad = core.read_pack(path)
        core.record_history(self._state, f"Installed pack {name}")
        core.install_pack_files(files, overwrite)
        mods = [b[:-4] for b in files if b.lower().endswith(".gsc")]
        if make_preset:
            self._state["presets"][name] = mods
            core.save_state(self._state)
        return len(mods)

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


def main():
    try:
        import webview
    except ImportError:
        core.run_ui()
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
    api._window = window  # private: pywebview would otherwise crawl the whole window object
    try:
        webview.start(gui="edgechromium", debug="--debug" in sys.argv)
    except Exception:
        core.run_ui()


if __name__ == "__main__":
    main()
