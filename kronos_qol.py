"""Kronos Plus - a companion app for the Kronos BO7 Zombies mod.

Works only with what Kronos exposes on disk: the custom_scripts folder,
kronos/settings.json, kronos/Logs, the bundled ACTS compiler and the
launcher. It never touches the game process or Kronos's internals.

Run:  python kronos_qol.py            (opens the window)
      python kronos_qol.py --selftest (prints what it finds, no window)
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import winreg
import zipfile

if getattr(sys, "frozen", False):
    # Packaged .exe: bundled files unpack to a temp folder, so state lives somewhere permanent.
    APP_DIR = sys._MEIPASS
    DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Kronos Plus")
    os.makedirs(DATA_DIR, exist_ok=True)
else:
    APP_DIR = DATA_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(DATA_DIR, "state.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
KRONOS_ROOT = r"C:\Kronos"
LAUNCHER = os.path.join(KRONOS_ROOT, "KronosLauncher.exe")
BO7_APPID = "1938090"
MAX_MOD_BYTES = 1024 * 1024
HISTORY_LIMIT = 50
NO_WINDOW = subprocess.CREATE_NO_WINDOW

# Files Kronos drops into a game folder; none of these belong in the Steam install.
KRONOS_MARKERS = ["kronos", "steam_settings", "steam_api64_gb.dll", "XINPUT9_1_0.dll", "steam_appid.txt"]


# ---------------------------------------------------------------- paths

def read_reg(path, name, hive=winreg.HKEY_CURRENT_USER):
    try:
        with winreg.OpenKey(hive, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def game_dir():
    return read_reg(r"Software\Kronos\Launcher", "GameDir") or os.path.join(KRONOS_ROOT, "cod25")


def kronos_dir():
    return os.path.join(game_dir(), "kronos")


def scripts_dir():
    # The launcher's "Scripts folder" setting is relative to cod25; blank means the default.
    custom = read_reg(r"Software\Kronos\Launcher", "ScriptsDir")
    if custom:
        return os.path.join(game_dir(), custom, "custom_scripts")
    return os.path.join(kronos_dir(), "custom_scripts")


def disabled_dir():
    # Kept outside custom_scripts so Kronos can't pick disabled mods up.
    return os.path.join(kronos_dir(), "custom_scripts_disabled")


def settings_path():
    return os.path.join(kronos_dir(), "settings.json")


def logs_dir():
    return os.path.join(kronos_dir(), "Logs")


def crash_file():
    return os.path.join(kronos_dir(), "crash", "crash.txt")


def acts_exe():
    return os.path.join(kronos_dir(), "tools", "acts.exe")


def steam_root():
    return read_reg(r"Software\Valve\Steam", "SteamPath") or r"C:\Program Files (x86)\Steam"


def steam_game_dir():
    return os.path.normpath(os.path.join(steam_root(), "steamapps", "common", "Call of Duty HQ", "cod25"))


def steam_manifest():
    return os.path.normpath(os.path.join(steam_root(), "steamapps", f"appmanifest_{BO7_APPID}.acf"))


# ---------------------------------------------------------------- app state

DEFAULT_STATE = {"presets": {}, "last_buildid": None, "history": [], "sessions": [],
                 "safe_mode_saved": None, "bisect": None, "dark": True,
                 "dev_mode": False, "test_alone": None, "launcher": None}


def launcher_path(state):
    """Kronos's launcher: the one the user picked, else next to the game folder, else C:\\Kronos."""
    for p in (state.get("launcher"), os.path.join(os.path.dirname(game_dir()), "KronosLauncher.exe"), LAUNCHER):
        if p and os.path.isfile(p):
            return p
    return None


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    for k, v in DEFAULT_STATE.items():
        state.setdefault(k, json.loads(json.dumps(v)))
    return state


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- mods

def mod_description(path):
    """Leading // comment lines of a .gsc file, joined."""
    lines = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                s = line.strip()
                if s.startswith("#using") or not s:
                    if lines:
                        break
                    continue
                if s.startswith("//"):
                    lines.append(s[2:].strip())
                else:
                    break
    except OSError:
        pass
    return " ".join(lines)


def mod_path(name):
    for folder in (scripts_dir(), disabled_dir()):
        p = os.path.join(folder, name + ".gsc")
        if os.path.exists(p):
            return p
    return None


def is_prepared(name):
    """Mods shipped with their own precompiled .gscc next to the .gsc (e.g. BO7 Mod Studio)."""
    p = mod_path(name)
    return bool(p) and os.path.exists(p[:-4] + ".gscc")


def list_mods():
    """[(name, enabled, description)] for every .gsc in the scripts and disabled folders."""
    mods = {}
    for folder, enabled in ((scripts_dir(), True), (disabled_dir(), False)):
        if not os.path.isdir(folder):
            continue
        for f in os.listdir(folder):
            if f.lower().endswith(".gsc"):
                name = f[:-4]
                man = _manifest_at(folder, name) or {}
                mods[name] = (name, enabled, man.get("description") or mod_description(os.path.join(folder, f)))
    return sorted(mods.values(), key=lambda m: m[0].lower())


def enabled_mods():
    return [n for n, on, _ in list_mods() if on]


def _move_mod(name, src, dst):
    os.makedirs(os.path.join(dst, "compiled"), exist_ok=True)
    # The .gsc plus any companions sharing its name (e.g. Mod Studio's .gscc and .bo7studio.json).
    for f in os.listdir(src):
        if f.startswith(name + ".") and os.path.isfile(os.path.join(src, f)):
            shutil.move(os.path.join(src, f), os.path.join(dst, f))
    # Move the compiled copy too, so a stale .gscc can't linger in the live folder.
    gscc = os.path.join(src, "compiled", name + ".gscc")
    if os.path.exists(gscc):
        shutil.move(gscc, os.path.join(dst, "compiled", name + ".gscc"))


def set_mod_enabled(name, enabled):
    src, dst = (disabled_dir(), scripts_dir()) if enabled else (scripts_dir(), disabled_dir())
    if os.path.exists(os.path.join(src, name + ".gsc")):
        _move_mod(name, src, dst)


def apply_enabled_set(names):
    names = set(names)
    for name, enabled, _ in list_mods():
        if enabled != (name in names):
            set_mod_enabled(name, name in names)


def check_mod_bytes(filename, data):
    """Return None if the data looks like a plain-text GSC mod, else the reason it doesn't."""
    if not filename.lower().endswith(".gsc"):
        return "Only .gsc files are mods. Never add an .exe or .dll someone calls a mod."
    if len(data) > MAX_MOD_BYTES:
        return f"File is {len(data) // 1024} KB, too large for a script mod."
    if b"\x00" in data or data[:2] == b"MZ":
        return "File contains binary data, so it isn't a plain-text script."
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return "File isn't readable text."
    return None


def check_mod_file(path):
    with open(path, "rb") as f:
        return check_mod_bytes(path, f.read())


def import_mod(path, overwrite=False):
    """Copy a checked .gsc into the scripts folder. Returns (ok, message)."""
    problem = check_mod_file(path)
    if problem:
        return False, problem
    name = os.path.basename(path)
    dest = os.path.join(scripts_dir(), name)
    if os.path.exists(dest) and not overwrite:
        return False, "exists"
    if os.path.exists(dest):
        backup_mod_file(dest)
    os.makedirs(scripts_dir(), exist_ok=True)
    shutil.copy2(path, dest)
    return True, f"Added {name}."


MOD_BACKUPS_KEPT = 30


def backup_mod_file(path):
    d = os.path.join(BACKUP_DIR, "mods")
    os.makedirs(d, exist_ok=True)
    base = os.path.basename(path)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, os.path.join(d, f"{stamp}-{base}"))
    # The editor backs up on every save, so keep only the newest copies of each file.
    old = sorted(f for f in os.listdir(d) if f.endswith("-" + base) and f[:8].isdigit())
    for f in old[:-MOD_BACKUPS_KEPT]:
        os.remove(os.path.join(d, f))


def save_mod_source(name, code):
    """Write edited source from the built-in editor, backing up the previous version first."""
    p = mod_path(name)
    if not p:
        raise ValueError(f"Mod {name} not found.")
    if is_prepared(name):
        raise ValueError("Precompiled mods can't be edited from source.")
    data = code.replace("\r\n", "\n").encode("utf-8")
    problem = check_mod_bytes(name + ".gsc", data)
    if problem:
        raise ValueError(problem)
    backup_mod_file(p)
    with open(p, "wb") as f:
        f.write(data)
    return os.path.getmtime(p)


def mod_mtime(name):
    p = mod_path(name)
    return os.path.getmtime(p) if p else None


# ---------------------------------------------------------------- history / undo

def record_history(state, action):
    """Snapshot which mods are on before a change, so it can be undone."""
    state["history"].append({"time": now_str(), "action": action, "before": enabled_mods()})
    state["history"] = state["history"][-HISTORY_LIMIT:]
    save_state(state)


def undo_last(state):
    if not state["history"]:
        return None
    last = state["history"].pop()
    apply_enabled_set(last["before"])
    save_state(state)
    return last["action"]


# ---------------------------------------------------------------- safe mode & crash bisect

def safe_mode_on(state):
    state["safe_mode_saved"] = enabled_mods()
    apply_enabled_set([])
    save_state(state)


def safe_mode_off(state):
    if state["safe_mode_saved"] is not None:
        apply_enabled_set(state["safe_mode_saved"])
        state["safe_mode_saved"] = None
        save_state(state)


def bisect_start(state):
    """Begin hunting for the mod that crashes the game by testing halves."""
    if state.get("test_alone"):
        return "Stop testing your mod first."
    mods = enabled_mods()
    if len(mods) < 2:
        return "Turn on at least 2 mods to search for a crashing one."
    state["bisect"] = {"original": mods, "suspects": mods, "testing": mods[: len(mods) // 2], "round": 1}
    apply_enabled_set(state["bisect"]["testing"])
    save_state(state)
    return None


def bisect_answer(state, crashed):
    """Feed back one test run. Returns the culprit's name once found, else None."""
    b = state["bisect"]
    suspects = b["testing"] if crashed else [m for m in b["suspects"] if m not in b["testing"]]
    if len(suspects) <= 1:
        culprit = suspects[0] if suspects else None
        apply_enabled_set(b["original"])
        state["bisect"] = None
        save_state(state)
        return culprit or "(none - the crash may need two mods together, or isn't caused by a mod)"
    b["suspects"] = suspects
    b["testing"] = suspects[: len(suspects) // 2]
    b["round"] += 1
    apply_enabled_set(b["testing"])
    save_state(state)
    return None


def bisect_cancel(state):
    if state["bisect"]:
        apply_enabled_set(state["bisect"]["original"])
        state["bisect"] = None
        save_state(state)


# ---------------------------------------------------------------- compile check (ACTS)

def compile_check(name):
    """Compile a mod with Kronos's bundled ACTS, like the game does at startup.
    Returns (ok: bool|None, message); None means it couldn't be checked."""
    if is_prepared(name):
        return None, "Prepared mod (ships its own compiled file), can't be checked from source."
    src = mod_path(name)
    if not src:
        return None, "Mod file not found."
    if not os.path.isfile(acts_exe()):
        return None, "Kronos's compiler (kronos\\tools\\acts.exe) not found."
    with tempfile.TemporaryDirectory() as tmp:
        try:
            r = subprocess.run(
                [acts_exe(), "-t", "gscc", src, "-o", os.path.join(tmp, name + ".gscc"),
                 "-g", "bo7", "--name", f"custom_scripts/{name}.gsc"],
                cwd=os.path.dirname(acts_exe()), capture_output=True, text=True,
                timeout=90, creationflags=NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as e:
            return None, f"Couldn't run the compiler: {e}"
        built = any(f.endswith(".gscc") for f in os.listdir(tmp))
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 0 and built:
        return True, "Compiles OK."
    lines = [l for l in out.splitlines() if l.strip() and "Unhandled exception" not in l]
    return False, "\n".join(lines[-6:]) or f"Compiler exited with code {r.returncode}."


# ---------------------------------------------------------------- conflict detector

ASSIGN = re.compile(r"\b(self|level|p|player|e)\s*\.\s*([A-Za-z_]\w*)(?:\s*\[[^\]]*\])?\s*(?<![=!<>])=(?!=)")
SETDVAR = re.compile(r'setdvar\s*\(\s*"([^"]+)"', re.I)


def find_conflicts():
    """Fields/dvars written by more than one enabled mod. [(what, [mods])]"""
    writers = {}
    for name in enabled_mods():
        if is_prepared(name):
            continue
        try:
            text = open(mod_path(name), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        text = re.sub(r"//[^\n]*", "", text)
        found = set()
        for owner, field in ASSIGN.findall(text):
            if field.lower().startswith(name.lower()):
                continue  # a mod's own guard flag, e.g. self.zm_start_points
            found.add(f"{'level' if owner == 'level' else 'player'}.{field}")
        for dvar in SETDVAR.findall(text):
            found.add(f'dvar "{dvar}"')
        for what in found:
            writers.setdefault(what, []).append(name)
    return sorted((w, m) for w, m in writers.items() if len(m) > 1)


# ---------------------------------------------------------------- templates

TEMPLATES = {
    "Starting points": {
        "param": ("Points", 10000),
        "code": '''#using script_4c770a9a4ad7659c;

// Start every player with {n} points.
autoexec {name}_init()
{{
    level namespace_42ffbe510c7bd5b1::function_3e93ae4f7823fe81(#"player_spawned", &{name}_spawned);
}}

{name}_spawned(params)
{{
    if (isdefined(self.{name}) || !self function_b36623eefe0028c8())
    {{
        return;
    }}
    self.{name} = 1;
    self thread {name}_give();
}}

{name}_give()
{{
    wait 1;
    if (!isdefined(self))
    {{
        return;
    }}
    if (!isdefined(self.score) || self.score < {n})
    {{
        self.score = {n};
    }}
}}
''',
    },
    "Bonus points every round": {
        "param": ("Points per round", 1000),
        "code": '''#using script_4c770a9a4ad7659c;

// Give every player {n} bonus points when each round starts.
autoexec {name}_init()
{{
    level namespace_42ffbe510c7bd5b1::function_3e93ae4f7823fe81("on_round_start", &{name}_round);
}}

{name}_round(params)
{{
    foreach (p in level.players)
    {{
        if (isdefined(p) && isdefined(p.score))
        {{
            p.score = p.score + {n};
        }}
    }}
}}
''',
    },
}


MOD_NAME = re.compile(r"[a-z][a-z0-9_]{2,40}")

# Starting point for a new dev project: runs once for each player who spawns.
SCAFFOLD = '''#using script_4c770a9a4ad7659c;

// {description}
autoexec {name}_init()
{{
    level namespace_42ffbe510c7bd5b1::function_3e93ae4f7823fe81(#"player_spawned", &{name}_spawned);
}}

{name}_spawned(params)
{{
    // Only once per player per match.
    if (isdefined(self.{name}_ready) || !self function_b36623eefe0028c8())
    {{
        return;
    }}
    self.{name}_ready = 1;
    self thread {name}_main();
}}

{name}_main()
{{
    wait 1;
    if (!isdefined(self))
    {{
        return;
    }}
    // Your code here. self is the player.
}}
'''


def _check_new_name(name):
    if not MOD_NAME.fullmatch(name):
        raise ValueError("Name must be 3-41 lowercase letters, digits or _, starting with a letter.")
    if mod_path(name):
        raise ValueError(f"A mod called {name} already exists.")


def _write_new_mod(name, code):
    os.makedirs(scripts_dir(), exist_ok=True)
    path = os.path.join(scripts_dir(), name + ".gsc")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(code)
    return path


def make_from_template(template, name, n):
    """Write a new mod from a template. Returns the path, or raises ValueError."""
    _check_new_name(name)
    return _write_new_mod(name, TEMPLATES[template]["code"].format(name=name, n=int(n)))


def create_project(name, manifest, template=None, n=None):
    """New dev project: the .gsc (blank scaffold or a template) plus its manifest."""
    if template:
        make_from_template(template, name, n)
    else:
        _check_new_name(name)
        desc = " ".join(str(manifest.get("description") or manifest.get("title") or name).split())
        _write_new_mod(name, SCAFFOLD.format(name=name, description=desc))
    return save_manifest(name, manifest)


# ---------------------------------------------------------------- manifests (<mod>.mod.json)

# Lives next to the .gsc, so _move_mod carries it along when the mod is turned on or off.
MANIFEST_SUFFIX = ".mod.json"
MODES = ("zm", "mp", "any")
REQ_NAME = re.compile(r"[A-Za-z0-9_\-]{1,64}")


def _manifest_at(folder, name):
    p = os.path.join(folder, name + MANIFEST_SUFFIX)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return clean_manifest(data) if isinstance(data, dict) else None


def load_manifest(name):
    p = mod_path(name)
    return _manifest_at(os.path.dirname(p), name) if p else None


def clean_manifest(data):
    """Keep known fields with sane types, so a hand-edited or downloaded manifest can't surprise us."""
    out = {}
    for k in ("title", "version", "author", "description"):
        v = data.get(k)
        if isinstance(v, (str, int, float)) and str(v).strip():
            out[k] = str(v).strip()[:500]
    out["mode"] = data.get("mode") if data.get("mode") in MODES else "any"
    req = data.get("requires")
    out["requires"] = sorted({r for r in req if isinstance(r, str) and REQ_NAME.fullmatch(r)})[:50] \
        if isinstance(req, list) else []
    return out


def default_manifest(name):
    try:
        author = get_path(load_settings(), ("player", "name"), "")
    except (OSError, ValueError):
        author = ""
    p = mod_path(name)
    mode = "zm" if name.startswith("zm_") else "mp" if name.startswith("mp_") else "any"
    return clean_manifest({"title": name, "version": "1.0.0", "author": author,
                           "description": mod_description(p) if p else "", "mode": mode})


def save_manifest(name, data):
    p = mod_path(name)
    if not p:
        raise ValueError(f"Mod {name} not found.")
    m = clean_manifest(data)
    m["requires"] = [r for r in m["requires"] if r != name]
    with open(p[:-4] + MANIFEST_SUFFIX, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=4)
    return m


def requirements(name):
    """The mod plus everything it requires, recursively (installed mods only)."""
    order, todo = [], [name]
    while todo:
        n = todo.pop()
        if n in order or not mod_path(n):
            continue
        order.append(n)
        todo.extend((load_manifest(n) or {}).get("requires", []))
    return order


# ---------------------------------------------------------------- linter

def _mask(code):
    """Blank out comments and string contents (keeping newlines and length) so rules only see code."""
    out, i, n = [], 0, len(code)
    blank = lambda s: re.sub(r"[^\n]", " ", s)
    while i < n:
        if code.startswith("//", i):
            j = code.find("\n", i)
            j = n if j < 0 else j
            out.append(blank(code[i:j]))
        elif code.startswith("/*", i):
            j = code.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(blank(code[i:j]))
        elif code[i] == '"':
            j = i + 1
            while j < n and code[j] not in '"\n':
                j += 2 if code[j] == "\\" else 1
            j = min(j, n)
            if j < n and code[j] == '"':
                j += 1
                out.append('"' + blank(code[i + 1:j - 1]) + '"')
            else:
                out.append(blank(code[i:j]))
        else:
            j = i + 1
            out.append(code[i])
        i = j
    return "".join(out)


def _match_brace(text, i):
    depth = 0
    for k in range(i, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return k
    return len(text) - 1


def _functions(masked):
    """[(header, body_start, body_end)] for each top-level { } block."""
    funcs, i, last = [], 0, 0
    while True:
        i = masked.find("{", i)
        if i < 0:
            return funcs
        end = _match_brace(masked, i)
        funcs.append((masked[last:i], i, end))
        last = i = end + 1


LOOP_FOREVER = re.compile(r"\bwhile\s*\(\s*(?:1|true)\s*\)|\bfor\s*\(\s*;\s*;\s*\)")
WAITS = re.compile(r"\bwait")  # wait, waittill*, waitframe, wait_network_frame...


def lint_source(code):
    """BO7 GSC gotchas the compiler doesn't catch. [{line, severity, rule, message}], sorted by line."""
    m = _mask(code)
    issues = []

    def add(idx, severity, rule, message):
        issues.append({"line": m.count("\n", 0, idx) + 1, "severity": severity, "rule": rule, "message": message})

    for x in LOOP_FOREVER.finditer(m):
        k = x.end()
        while k < len(m) and m[k].isspace():
            k += 1
        if k < len(m) and m[k] == "{":
            body = m[k:_match_brace(m, k) + 1]
        else:
            e = m.find(";", k)
            body = m[k:len(m) if e < 0 else e + 1]
        if WAITS.search(body):
            continue
        if re.search(r"\b(break|return)\b", body):
            add(x.start(), "warning", "loop-no-wait",
                "Endless loop with no wait. Unless it always exits right away, it will freeze the game.")
        else:
            add(x.start(), "error", "loop-no-wait",
                "Endless loop with no wait: this freezes the game. Put a wait inside it, e.g. wait 0.05;")

    for header, start, end in _functions(m):
        if re.search(r"\bautoexec\b", header):
            continue  # self is level there
        waited = None
        for tok in re.finditer(r"\bwait\b|\bisdefined\s*\(\s*self\s*\)|\bself\b", m[start:end]):
            t = tok.group(0)
            if t == "wait":
                waited = waited if waited is not None else start + tok.start()
            elif t.startswith("isdefined"):
                waited = None
            elif waited is not None:
                add(start + tok.start(), "warning", "self-after-wait",
                    "Uses self after a wait without checking isdefined(self). If the player leaves during the "
                    "wait, this line errors. Add: if (!isdefined(self)) return;")
                waited = None

    if not re.search(r"^\s*#using\b", m, re.M):
        ns = re.search(r"\bnamespace_\w+\s*::", m)
        if ns:
            add(ns.start(), "warning", "missing-using",
                "Calls a namespace_…:: function but has no #using line. It probably needs the #using for "
                "the script that defines it (copy it from a mod where the same call works).")

    if re.search(r"\b(?:iprintln|iprintlnbold|println)\s*\(", m):
        x = re.search(r"\b(?:iprintln|iprintlnbold|println)\s*\(", m)
        add(x.start(), "info", "debug-print", "Has on-screen/debug prints. Fine while testing; remove before release.")

    return sorted(issues, key=lambda i: i["line"])


def lint_mod(name):
    """Source lint plus manifest checks for one installed mod."""
    p = mod_path(name)
    if not p or is_prepared(name):
        return []
    with open(p, encoding="utf-8", errors="replace") as f:
        issues = lint_source(f.read())
    man = load_manifest(name)
    if man is None:
        issues.append({"line": 0, "severity": "info", "rule": "no-manifest",
                       "message": "No manifest yet. Add a title, version and author in Studio so players know what this is."})
    else:
        on = set(enabled_mods())
        for r in man["requires"]:
            if not mod_path(r):
                issues.append({"line": 0, "severity": "error", "rule": "missing-requirement",
                               "message": f"Requires {r}, which isn't installed."})
            elif name in on and r not in on:
                issues.append({"line": 0, "severity": "warning", "rule": "requirement-off",
                               "message": f"Requires {r}, which is turned off."})
    return issues


GSC_KEYWORDS = ["autoexec", "function", "if", "else", "for", "foreach", "in", "while", "return", "wait", "waittill",
                "waittillframeend", "thread", "endon", "notify", "self", "level", "isdefined", "undefined", "true",
                "false", "break", "continue", "switch", "case", "default", "getdvarint", "getdvarfloat", "getdvar",
                "setdvar", "#using", "#namespace", "array", "isplayer"]
WORD = re.compile(r'namespace_\w+::function_\w+|#"[a-z0-9_]+"|\b[A-Za-z_][A-Za-z0-9_]{3,}\b')


def completion_words():
    """Words for the editor's autocomplete: keywords plus everything used in installed source mods,
    so calls known to work in BO7 (e.g. the player_spawned hook) are one Tab away."""
    words = {k: "keyword" for k in GSC_KEYWORDS}
    for name, _, _ in list_mods():
        if is_prepared(name):
            continue
        try:
            with open(mod_path(name), encoding="utf-8", errors="replace") as f:
                code = f.read()
        except OSError:
            continue
        for w in WORD.findall(re.sub(r"//[^\n]*", "", code)):
            words.setdefault(w, name)
    return [{"w": w, "from": src} for w, src in sorted(words.items(), key=lambda x: x[0].lower())][:4000]


COMPILE_LINE = re.compile(r"#(\d+):(\d+)\s+(.*)")


def compile_error_line(msg):
    """(line, text) from an ACTS error like 'file.gsc#6:9 no viable alternative', else (None, msg)."""
    for l in (msg or "").splitlines():
        x = COMPILE_LINE.search(l)
        if x:
            text = x.group(3)
            if "no viable alternative" in text or "mismatched input" in text:
                text += " (often a missing ; or ) at the end of the line before)"
            return int(x.group(1)), text
    return None, msg


# ---------------------------------------------------------------- test a mod alone

def test_alone_start(state, name):
    """Turn on only this mod (and what it requires), remembering the real set. Returns an error or None."""
    if state.get("bisect"):
        return "Finish or cancel the crash search first."
    if state.get("safe_mode_saved") is not None:
        return "Turn safe mode off first."
    if not mod_path(name):
        return f"Mod {name} not found."
    if not state.get("test_alone"):
        state["test_alone"] = {"saved": enabled_mods()}
    state["test_alone"]["mod"] = name
    apply_enabled_set(requirements(name))
    save_state(state)
    return None


def test_alone_stop(state):
    t = state.get("test_alone")
    if t:
        apply_enabled_set(t["saved"])
        state["test_alone"] = None
        save_state(state)


def editor_exe():
    """VS Code if it's installed, else None."""
    candidates = [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "Code.exe"),
                  os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Microsoft VS Code", "Code.exe")]
    cli = shutil.which("code")
    if cli:  # ...\Microsoft VS Code\bin\code.cmd
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(cli)), "Code.exe"))
    return next((c for c in candidates if os.path.isfile(c)), None)


# ---------------------------------------------------------------- mod packs

PACK_INFO = "kronos_qol_pack.json"


def export_pack(zip_path, pack_name):
    """Zip the enabled source mods (.gsc only) plus a manifest. Returns (included, skipped)."""
    included, skipped = [], []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in enabled_mods():
            if is_prepared(name):
                skipped.append(name)
                continue
            z.write(mod_path(name), name + ".gsc")
            man = load_manifest(name)
            if man:
                z.writestr(name + MANIFEST_SUFFIX, json.dumps(man, indent=4))
            included.append(name)
        z.writestr(PACK_INFO, json.dumps({"name": pack_name, "mods": included, "made": now_str()}, indent=4))
    return included, skipped


def read_pack(zip_path):
    """Validate a mod pack without extracting. Returns (pack_name, {filename: bytes}, [rejected msgs])."""
    good, bad, pack_name = {}, [], os.path.splitext(os.path.basename(zip_path))[0]
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            base = os.path.basename(info.filename)
            if base == PACK_INFO:
                try:
                    pack_name = json.loads(z.read(info)).get("name") or pack_name
                except ValueError:
                    pass
                continue
            # Mods shared online are often zipped inside folders: take each file by its own name.
            base = info.filename.replace("\\", "/").rstrip("/").split("/")[-1]
            if base.lower().endswith((".exe", ".dll", ".sys", ".bat", ".cmd", ".ps1", ".scr", ".vbs")):
                bad.append(f"{info.filename}: programs are never installed. Be careful with any mod that ships one.")
                continue
            if not base.lower().endswith((".gsc", MANIFEST_SUFFIX)):
                bad.append(f"{info.filename}: not a .gsc mod, ignored")
                continue
            if base in good:
                bad.append(f"{info.filename}: another {base} is already in this zip, ignored")
                continue
            if info.file_size > MAX_MOD_BYTES:
                bad.append(f"{base}: too large")
                continue
            data = z.read(info)
            if base.lower().endswith(MANIFEST_SUFFIX):
                try:
                    man = json.loads(data.decode("utf-8"))
                    if not isinstance(man, dict):
                        raise ValueError
                except ValueError:
                    bad.append(f"{base}: not a valid manifest")
                    continue
                good[base] = json.dumps(clean_manifest(man), indent=4).encode("utf-8")
                continue
            problem = check_mod_bytes(base, data)
            if problem:
                bad.append(f"{base}: {problem}")
            else:
                good[base] = data
    return pack_name, good, bad


# Only Discord's own file servers: a pasted link can't make the app download from anywhere else.
LINK_HOSTS = ("cdn.discordapp.com", "media.discordapp.net")
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
DOWNLOAD_PREFIX = "kronos-plus-dl-"


def download_mod_link(url):
    """Download a .gsc mod or .zip pack from a Discord file link into a temp folder; returns its path.

    Raises ValueError with a message for the user. Nothing is installed here: the caller
    runs the same safety checks as for files picked from disk.
    """
    parts = urllib.parse.urlsplit((url or "").strip())
    if parts.scheme != "https" or parts.hostname not in LINK_HOSTS:
        raise ValueError("Paste a Discord file link: right-click the file in Discord and choose Copy Link.")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", os.path.basename(urllib.parse.unquote(parts.path)))
    if name.lower().endswith((".rar", ".7z")):
        raise ValueError(f"{name} is a .rar/.7z archive, which Kronos Plus can't open. Extract it yourself and use "
                         "Add .gsc mods, or ask the author for a .zip.")
    if not name.lower().endswith((".gsc", ".zip")):
        raise ValueError(f"{name or 'That link'} isn't a .gsc mod or a .zip of mods.")
    request = urllib.request.Request(parts.geturl(), headers={"User-Agent": "KronosPlus"})
    try:
        with urllib.request.urlopen(request, timeout=30) as r:
            if urllib.parse.urlsplit(r.geturl()).hostname not in LINK_HOSTS:
                raise ValueError("That link redirected away from Discord, so it wasn't downloaded.")
            data = r.read(MAX_DOWNLOAD_BYTES + 1)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            raise ValueError("Discord says that link has expired. Copy a fresh link from Discord and try again.")
        raise ValueError(f"Discord refused the download (error {e.code}). Try again in a moment.")
    except (urllib.error.URLError, OSError):
        raise ValueError("Couldn't download it. Check your internet connection and try again.")
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError("That file is too large to be a mod.")
    path = os.path.join(tempfile.mkdtemp(prefix=DOWNLOAD_PREFIX), name)
    with open(path, "wb") as f:
        f.write(data)
    return path


def forget_download(path):
    """Delete a file download_mod_link made (and its temp folder); leaves anything else alone."""
    folder = os.path.dirname(path)
    if os.path.basename(folder).startswith(DOWNLOAD_PREFIX) and os.path.dirname(folder) == tempfile.gettempdir():
        shutil.rmtree(folder, ignore_errors=True)


def install_pack_files(files, overwrite_names=()):
    os.makedirs(scripts_dir(), exist_ok=True)
    for base, data in files.items():
        dest = os.path.join(scripts_dir(), base)
        if os.path.exists(dest):
            if base not in overwrite_names:
                continue
            backup_mod_file(dest)
        with open(dest, "wb") as f:
            f.write(data)


# ---------------------------------------------------------------- settings

# (label, json path, invert) - invert shows a "disable" flag as an "enable" checkbox.
SETTING_FLAGS = [
    ("Custom scripts enabled", ("server", "disableGsc"), True),
    ("Cheats (sv_cheats)", ("server", "sv_cheats"), False),
    ("Texture streaming", ("graphics", "textureStreaming"), False),
    ("Logging", ("logging", "enabled"), False),
    ("Log GSC print()", ("logging", "gsc", "logPrintEnabled"), False),
    ("Log GSC strings", ("logging", "gsc", "logStringEnabled"), False),
    ("Log GSC sys prints", ("logging", "gsc", "sysPrintEnabled"), False),
    ("Detailed GSC stack traces", ("logging", "gsc", "detailedStackTrace"), False),
]
SETTING_TEXTS = [
    ("Player name", ("player", "name")),
    ("Menu key", ("keys", "menu")),
    ("Noclip key", ("keys", "noclip")),
]


def get_path(d, path, default=None):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d


def set_path(d, path, value):
    for p in path[:-1]:
        d = d.setdefault(p, {})
    d[path[-1]] = value


def load_settings():
    with open(settings_path(), encoding="utf-8") as f:
        return json.load(f)


def backup_settings():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"settings-{stamp}.json")
    shutil.copy2(settings_path(), dest)
    return dest


def save_settings(data):
    backup_settings()
    with open(settings_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted((f for f in os.listdir(BACKUP_DIR) if f.startswith("settings-") and f.endswith(".json")), reverse=True)


def restore_settings(backup_name):
    src = os.path.join(BACKUP_DIR, backup_name)
    with open(src, encoding="utf-8") as f:
        json.load(f)  # refuse to restore a broken file
    backup_settings()
    shutil.copy2(src, settings_path())


# ---------------------------------------------------------------- logs

LOG_HIGHLIGHT = re.compile(r"(?i)error|fail|fault|\bgsc:|\[custom gsc\]|crash|exception")


def list_logs():
    files = []
    if os.path.isdir(logs_dir()):
        files += [os.path.join(logs_dir(), f) for f in os.listdir(logs_dir())]
    if os.path.exists(crash_file()):
        files.append(crash_file())
    return sorted((f for f in files if os.path.isfile(f)), key=os.path.getmtime, reverse=True)


def read_log(path, max_bytes=512 * 1024):
    with open(path, "rb") as f:
        f.seek(max(0, os.path.getsize(path) - max_bytes))
        return f.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------- live console

CONSOLE_ERROR = re.compile(r"(?i)error|fail|fault|crash|exception")
CONSOLE_SCRIPT = re.compile(r"(?i)\bgsc\b|\[custom gsc\]|custom_scripts")


def matches_log():
    return os.path.join(game_dir(), "players", "zm_matches.log")


def console_files():
    """Every text file Kronos writes while you play."""
    files = []
    if os.path.isdir(logs_dir()):
        files += [os.path.join(logs_dir(), f) for f in sorted(os.listdir(logs_dir()))]
    files += [os.path.join(kronos_dir(), "launcher.log"), crash_file(), matches_log()]
    return [f for f in files if os.path.isfile(f)]


def parse_match(line):
    """A Zombies match summary from a zm_matches.log match_end line, else None."""
    parts = line.rstrip("\n").split("\t")
    f = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
    if f.get("event") != "dlog_event_zm_player_match_end":
        return None
    num = lambda k: int(f[k]) if f.get(k, "").lstrip("-").isdigit() else 0
    try:
        when = datetime.datetime.fromtimestamp(int(parts[0])).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, OverflowError):
        when = ""
    return {"time": when, "map": f.get("map", "?"), "round": num("player_quit_round_number"),
            "kills": num("eliminations"), "crits": num("critical_kills"), "seconds": num("time_played"),
            "solo": f.get("is_solo_match") == "1", "xp": num("total_xp"), "downs": num("downs")}


def match_text(m):
    mins, secs = divmod(m["seconds"], 60)
    return (f"Match ended on {m['map']}: round {m['round']}, {m['kills']} kills "
            f"({m['crits']} crits), {mins}m {secs:02d}s played")


def console_read(cursor, tail=40, max_bytes=256 * 1024):
    """New lines from console_files() since cursor ({path: offset}); a missing cursor means
    'start with the last few lines'. Returns (rows, new_cursor)."""
    first = cursor is None
    cursor = dict(cursor or {})
    rows = []
    for path in console_files():
        size = os.path.getsize(path)
        start = cursor.get(path, 0)
        if start > size:  # file was replaced or truncated
            start = 0
        if first:
            start = max(0, size - max_bytes)
        with open(path, "rb") as f:
            f.seek(start)
            chunk = f.read(max_bytes)
        # Only consume whole lines, so a half-written line is read complete next time
        # (except on the first read, where a last line without a newline is still worth showing).
        nl = chunk.rfind(b"\n")
        if first or (nl < 0 and len(chunk) == max_bytes):
            end = len(chunk)
        else:
            end = nl + 1
        cursor[path] = start + end
        lines = chunk[:end].decode("utf-8", errors="replace").splitlines()
        src = os.path.basename(path)
        is_matches = os.path.normcase(path) == os.path.normcase(matches_log())
        new = []
        for line in lines:
            if not line.strip():
                continue
            if is_matches:
                m = parse_match(line)
                if m:
                    new.append({"src": src, "kind": "match", "text": match_text(m), "match": m})
                continue  # per-weapon lines are noise in a console
            kind = "error" if CONSOLE_ERROR.search(line) else "script" if CONSOLE_SCRIPT.search(line) else "info"
            new.append({"src": src, "kind": kind, "text": line})
        rows += new[-tail:] if first else new
    return rows, cursor


# ---------------------------------------------------------------- play sessions

def running_processes():
    """Lowercase exe names of running programs, read straight from Windows (no hidden tasklist runs)."""
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.Process32FirstW.argtypes = k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if not snap or snap == wintypes.HANDLE(-1).value:
        return set()
    names = set()
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            names.add(entry.szExeFile.lower())
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return names


class SessionTracker:
    """Notices when the game runs while Kronos's launcher is open, and logs each session."""

    def __init__(self, state):
        self.state = state
        self.current = None

    def poll(self):
        procs = running_processes()
        playing = "cod25-cod.exe" in procs and "kronoslauncher.exe" in procs
        if playing and not self.current:
            self.current = {"start": time.time(), "mods": enabled_mods()}
        elif not playing and self.current and "cod25-cod.exe" not in procs:
            start = self.current["start"]
            crashed = os.path.exists(crash_file()) and os.path.getmtime(crash_file()) > start
            self.state["sessions"].append({
                "start": datetime.datetime.fromtimestamp(start).strftime("%Y-%m-%d %H:%M"),
                "minutes": round((time.time() - start) / 60),
                "mods": self.current["mods"],
                "crash": crashed,
            })
            self.state["sessions"] = self.state["sessions"][-200:]
            save_state(self.state)
            self.current = None
            return "ended"
        return "playing" if self.current else "idle"


def crash_suspects(state):
    """Mods most often on during crashed sessions vs clean ones: [(mod, crash_rate, sessions)]."""
    stats = {}
    for s in state["sessions"]:
        for m in s["mods"]:
            c, t = stats.get(m, (0, 0))
            stats[m] = (c + (1 if s["crash"] else 0), t + 1)
    return sorted(((m, c / t, t) for m, (c, t) in stats.items() if c), key=lambda x: -x[1])


# ---------------------------------------------------------------- health

def steam_buildid():
    try:
        with open(steam_manifest(), encoding="utf-8") as f:
            m = re.search(r'"buildid"\s+"(\d+)"', f.read())
            return m.group(1) if m else None
    except OSError:
        return None


def steam_updated(state):
    build, last = steam_buildid(), state.get("last_buildid")
    return bool(build and last and build != last), last, build


def health_checks(state):
    """[(ok: bool|None, title, detail)]; None means couldn't check."""
    results = []
    gd = game_dir()
    exe_ok = os.path.isfile(os.path.join(gd, "cod25-cod.exe"))
    results.append((exe_ok, "Kronos game folder", gd if exe_ok else f"{gd} has no cod25-cod.exe"))

    in_steam = "steamapps" in gd.lower()
    results.append((not in_steam, "Kronos isn't pointed at Steam",
                    "OK" if not in_steam else "The launcher's game folder is your Steam install. Change it to your separate Kronos copy of the game."))

    sd = steam_game_dir()
    if os.path.isdir(sd):
        found = [m for m in KRONOS_MARKERS if os.path.exists(os.path.join(sd, m))]
        results.append((not found, "Steam install is clean",
                        "No Kronos files" if not found else "Kronos files in Steam folder: " + ", ".join(found)))
    else:
        results.append((None, "Steam install is clean", f"Steam folder not found at {sd}"))

    updated, last, build = steam_updated(state)
    if build is None:
        results.append((None, "BO7 updates", "Couldn't read Steam's BO7 build number"))
    elif updated:
        results.append((False, "BO7 updates",
                        f"Steam updated BO7 (build {last} -> {build}). Your Kronos copy may need refreshing; "
                        "check the Kronos Discord before playing. Click 'Mark update as handled' when done."))
    else:
        results.append((True, "BO7 updates", f"No new Steam update (build {build})"))
        if not last:
            state["last_buildid"] = build
            save_state(state)

    conflicts = find_conflicts()
    results.append((not conflicts, "Mod conflicts",
                    "None found" if not conflicts else
                    "; ".join(f"{w} is changed by {', '.join(m)}" for w, m in conflicts)))
    return results


def prelaunch_problems(state):
    """Quick checks before opening the launcher. Returns a list of human-readable problems."""
    problems = []
    for ok, title, detail in health_checks(state):
        if ok is False:
            problems.append(f"{title}: {detail}")
    for name in enabled_mods():
        ok, msg = compile_check(name)
        if ok is False:
            problems.append(f"Mod {name} doesn't compile: {msg.splitlines()[-1] if msg else ''}")
        for issue in lint_mod(name):
            if issue["severity"] == "error":
                where = f" (line {issue['line']})" if issue["line"] else ""
                problems.append(f"Mod {name}{where}: {issue['message']}")
    if state.get("bisect"):
        problems.append("A crash search is in progress, so only some of your mods are on.")
    if state.get("safe_mode_saved") is not None:
        problems.append("Safe mode is on, so all mods are off.")
    return problems


# ---------------------------------------------------------------- UI

LIGHT = {"bg": "#f3f3f3", "fg": "#1b1b1b", "field": "#ffffff", "sel": "#cfe3ff", "muted": "#666666", "hit": "#ffe2e2"}
DARK = {"bg": "#1f2124", "fg": "#e6e6e6", "field": "#2a2d31", "sel": "#3a5a8c", "muted": "#9aa0a6", "hit": "#5a2a2a"}


def run_ui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk

    state = load_state()
    tracker = SessionTracker(state)
    root = tk.Tk()
    root.title("Kronos Plus")
    icon = os.path.join(APP_DIR, "kronos_plus.ico")
    if os.path.isfile(icon):
        root.iconbitmap(icon)
    root.geometry("1000x680")
    root.minsize(800, 520)
    style = ttk.Style(root)
    style.theme_use("clam")
    plain_widgets = []  # tk (non-ttk) widgets that need manual theming

    def apply_theme():
        c = DARK if state["dark"] else LIGHT
        root.configure(bg=c["bg"])
        style.configure(".", background=c["bg"], foreground=c["fg"], fieldbackground=c["field"])
        style.configure("Treeview", background=c["field"], foreground=c["fg"], fieldbackground=c["field"])
        style.map("Treeview", background=[("selected", c["sel"])])
        style.configure("TNotebook.Tab", padding=(12, 4))
        style.map("TNotebook.Tab", background=[("selected", c["field"])])
        style.configure("Muted.TLabel", foreground=c["muted"])
        style.configure("Banner.TLabel", background="#c62828", foreground="white", padding=6)
        for w in plain_widgets:
            w.configure(bg=c["field"], fg=c["fg"], selectbackground=c["sel"], highlightthickness=0)
            if isinstance(w, tk.Text):
                w.configure(insertbackground=c["fg"])
        tree.tag_configure("off", foreground=c["muted"])
        log_text.tag_configure("hit", background=c["hit"])

    def plain(w):
        plain_widgets.append(w)
        return w

    # ---- top bar
    top = ttk.Frame(root, padding=(10, 8))
    top.pack(fill="x")
    ttk.Label(top, text="Kronos Plus", font=("Segoe UI", 14, "bold")).pack(side="left")
    status_var = tk.StringVar()
    ttk.Label(top, textvariable=status_var, style="Muted.TLabel").pack(side="left", padx=12)

    def toggle_dark():
        state["dark"] = not state["dark"]
        save_state(state)
        apply_theme()

    def play():
        launcher = launcher_path(state)
        if not launcher:
            launcher = filedialog.askopenfilename(title="Where is KronosLauncher.exe?",
                                                  filetypes=[("Kronos launcher", "KronosLauncher.exe")])
            if not launcher:
                return
            state["launcher"] = launcher
            save_state(state)
        root.config(cursor="watch")
        root.update()
        problems = prelaunch_problems(state)
        root.config(cursor="")
        if problems and not messagebox.askyesno(
                "Before you play", "Found some things to check:\n\n• " + "\n• ".join(problems) +
                "\n\nOpen the Kronos launcher anyway?"):
            return
        os.startfile(launcher)

    ttk.Button(top, text="▶  Check & open Kronos launcher", command=play).pack(side="right")
    ttk.Button(top, text="◐ Dark mode", command=toggle_dark).pack(side="right", padx=6)

    banner = ttk.Label(root, style="Banner.TLabel")

    def refresh_banner():
        msgs = []
        updated, last, build = steam_updated(state)
        if updated:
            msgs.append(f"Steam updated BO7 (build {last} → {build}). Check the Kronos Discord before playing.")
        if state.get("safe_mode_saved") is not None:
            msgs.append("Safe mode is on: all mods are off.")
        if state.get("bisect"):
            b = state["bisect"]
            msgs.append(f"Crash search round {b['round']}: testing {len(b['testing'])} of {len(b['suspects'])} suspects.")
        if msgs:
            banner.configure(text="   ".join(msgs))
            banner.pack(fill="x", padx=10, after=top)
        else:
            banner.pack_forget()

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    # ================================================================ Mods tab
    mods_tab = ttk.Frame(nb, padding=8)
    nb.add(mods_tab, text="Mods")

    left = ttk.Frame(mods_tab)
    left.pack(side="left", fill="both", expand=True)
    search_var = tk.StringVar()
    sbar = ttk.Frame(left)
    sbar.pack(fill="x", pady=(0, 6))
    ttk.Label(sbar, text="Search").pack(side="left")
    ttk.Entry(sbar, textvariable=search_var).pack(side="left", fill="x", expand=True, padx=6)

    pane = ttk.PanedWindow(left, orient="vertical")
    pane.pack(fill="both", expand=True)
    tree_frame = ttk.Frame(pane)
    tree = ttk.Treeview(tree_frame, columns=("status", "name", "desc"), show="headings", selectmode="extended")
    for c, w, label in (("status", 70, "Status"), ("name", 220, "Mod"), ("desc", 420, "Description")):
        tree.heading(c, text=label)
        tree.column(c, width=w, stretch=(c == "desc"))
    tree.pack(fill="both", expand=True)
    pane.add(tree_frame, weight=3)

    detail = ttk.Frame(pane)
    dbar = ttk.Frame(detail)
    dbar.pack(fill="x", pady=(6, 2))
    detail_title = tk.StringVar(value="Select a mod to see its code")
    ttk.Label(dbar, textvariable=detail_title, font=("Segoe UI", 10, "bold")).pack(side="left")
    src_text = plain(tk.Text(detail, height=10, wrap="none", font=("Consolas", 9)))
    src_text.pack(fill="both", expand=True)
    pane.add(detail, weight=2)

    side = ttk.Frame(mods_tab, padding=(10, 0))
    side.pack(side="right", fill="y")

    def refresh_mods():
        q = search_var.get().lower().strip()
        keep = set(tree.selection())
        tree.delete(*tree.get_children())
        for name, enabled, desc in list_mods():
            if q and q not in name.lower() and q not in desc.lower():
                continue
            status = ("On" if enabled else "Off") + (" ⓟ" if is_prepared(name) else "")
            tree.insert("", "end", iid=name, values=(status, name, desc), tags=() if enabled else ("off",))
        tree.selection_set([k for k in keep if tree.exists(k)])
        refresh_presets()
        refresh_banner()
        status_var.set(f"{len(enabled_mods())} mods on · game folder {game_dir()}")

    search_var.trace_add("write", lambda *_: refresh_mods())

    def show_source(_=None):
        sel = tree.selection()
        src_text.configure(state="normal")
        src_text.delete("1.0", "end")
        if len(sel) == 1:
            p = mod_path(sel[0])
            detail_title.set(f"{sel[0]}.gsc" + ("   (prepared mod: real code is precompiled)" if is_prepared(sel[0]) else ""))
            if p:
                src_text.insert("end", open(p, encoding="utf-8", errors="replace").read())
        else:
            detail_title.set(f"{len(sel)} mods selected" if sel else "Select a mod to see its code")
        src_text.configure(state="disabled")

    tree.bind("<<TreeviewSelect>>", show_source)

    def selected():
        names = list(tree.selection())
        if not names:
            messagebox.showinfo("Kronos Plus", "Select one or more mods first.")
        return names

    def toggle(enabled):
        names = selected()
        if names:
            record_history(state, f"Turned {'on' if enabled else 'off'} {', '.join(names)}")
            for n in names:
                set_mod_enabled(n, enabled)
            refresh_mods()

    def toggle_clicked(event):
        name = tree.identify_row(event.y)
        if name:
            record_history(state, f"Toggled {name}")
            set_mod_enabled(name, name not in enabled_mods())
            refresh_mods()

    tree.bind("<Double-1>", toggle_clicked)

    def do_import():
        paths = filedialog.askopenfilenames(title="Add .gsc mods", filetypes=[("GSC mods", "*.gsc")])
        if not paths:
            return
        record_history(state, "Added mods")
        msgs = []
        for p in paths:
            ok, msg = import_mod(p)
            if msg == "exists":
                if messagebox.askyesno("Kronos Plus", f"{os.path.basename(p)} already exists. Replace it? (The old one is backed up.)"):
                    ok, msg = import_mod(p, overwrite=True)
                else:
                    msg = f"Skipped {os.path.basename(p)}."
            msgs.append(msg if ok else f"{os.path.basename(p)}: {msg}")
        messagebox.showinfo("Kronos Plus", "\n".join(msgs))
        refresh_mods()

    def check_selected():
        names = list(tree.selection()) or enabled_mods()
        root.config(cursor="watch")
        root.update()
        lines = []
        for n in names:
            ok, msg = compile_check(n)
            mark = {True: "✔", False: "✖", None: "–"}[ok]
            lines.append(f"{mark} {n}: {msg}")
        root.config(cursor="")
        messagebox.showinfo("Compile check", "\n\n".join(lines))

    def undo():
        action = undo_last(state)
        messagebox.showinfo("Kronos Plus", f"Undid: {action}" if action else "Nothing to undo.")
        refresh_mods()

    def new_mod():
        win = tk.Toplevel(root)
        win.title("New mod from template")
        win.configure(bg=(DARK if state["dark"] else LIGHT)["bg"])
        f = ttk.Frame(win, padding=14)
        f.pack(fill="both", expand=True)
        tpl = tk.StringVar(value=list(TEMPLATES)[0])
        name_var, num_var = tk.StringVar(value="zm_my_mod"), tk.StringVar()
        num_label = tk.StringVar()

        def on_tpl(*_):
            label, default = TEMPLATES[tpl.get()]["param"]
            num_label.set(label)
            num_var.set(str(default))

        ttk.Label(f, text="Template").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Combobox(f, textvariable=tpl, values=list(TEMPLATES), state="readonly", width=28).grid(row=0, column=1, pady=3)
        ttk.Label(f, text="Mod name").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(f, textvariable=name_var, width=30).grid(row=1, column=1, pady=3)
        ttk.Label(f, textvariable=num_label).grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(f, textvariable=num_var, width=30).grid(row=2, column=1, pady=3)
        tpl.trace_add("write", on_tpl)
        on_tpl()

        def create():
            try:
                n = int(num_var.get())
                record_history(state, f"Created {name_var.get()}")
                make_from_template(tpl.get(), name_var.get().strip(), n)
            except ValueError as e:
                messagebox.showerror("Kronos Plus", str(e) if str(e) else "Enter a whole number.", parent=win)
                return
            ok, msg = compile_check(name_var.get().strip())
            win.destroy()
            refresh_mods()
            messagebox.showinfo("Kronos Plus", f"Created {name_var.get()}.gsc\nCompile check: {msg}")

        ttk.Button(f, text="Create", command=create).grid(row=3, column=1, sticky="e", pady=(10, 0))

    def export_ui():
        p = filedialog.asksaveasfilename(title="Save mod pack", defaultextension=".zip",
                                         filetypes=[("Mod pack", "*.zip")], initialfile="my_kronos_mods.zip")
        if not p:
            return
        inc, skip = export_pack(p, os.path.splitext(os.path.basename(p))[0])
        msg = f"Saved {len(inc)} mods to {os.path.basename(p)}."
        if skip:
            msg += "\n\nSkipped prepared mods (no readable source to share): " + ", ".join(skip)
        messagebox.showinfo("Kronos Plus", msg)

    def import_pack_ui():
        p = filedialog.askopenfilename(title="Open mod pack", filetypes=[("Mod pack", "*.zip")])
        if not p:
            return
        try:
            pack_name, files, bad = read_pack(p)
        except zipfile.BadZipFile:
            messagebox.showerror("Kronos Plus", "That isn't a valid .zip file.")
            return
        if not any(b.lower().endswith(".gsc") for b in files):
            messagebox.showerror("Kronos Plus", "No usable .gsc mods in that pack.\n\n" + "\n".join(bad))
            return
        existing = [b for b in files if os.path.exists(os.path.join(scripts_dir(), b))]
        overwrite = existing if existing and messagebox.askyesno(
            "Kronos Plus", "These mods already exist:\n" + "\n".join(existing) + "\n\nReplace them? (Old ones are backed up.)") else []
        record_history(state, f"Installed pack {pack_name}")
        install_pack_files(files, overwrite)
        names = [b[:-4] for b in files if b.lower().endswith(".gsc")]
        if messagebox.askyesno("Kronos Plus", f"Installed {len(names)} mods from '{pack_name}'." +
                               (f"\nRejected:\n" + "\n".join(bad) if bad else "") +
                               f"\n\nSave them as preset '{pack_name}'?"):
            state["presets"][pack_name] = names
            save_state(state)
        refresh_mods()

    def open_folder():
        os.makedirs(scripts_dir(), exist_ok=True)
        os.startfile(scripts_dir())

    def open_in_notepad():
        sel = tree.selection()
        if len(sel) == 1 and mod_path(sel[0]):
            subprocess.Popen(["notepad.exe", mod_path(sel[0])])

    for text, cmd in (("Turn on", lambda: toggle(True)), ("Turn off", lambda: toggle(False)),
                      ("Undo last change", undo)):
        ttk.Button(side, text=text, command=cmd).pack(fill="x", pady=2)
    ttk.Separator(side).pack(fill="x", pady=8)
    for text, cmd in (("New mod from template…", new_mod), ("Add .gsc mods…", do_import),
                      ("Check mods compile", check_selected), ("Edit in Notepad", open_in_notepad),
                      ("Open scripts folder", open_folder)):
        ttk.Button(side, text=text, command=cmd).pack(fill="x", pady=2)
    ttk.Separator(side).pack(fill="x", pady=8)
    ttk.Label(side, text="Presets").pack(anchor="w")
    preset_var = tk.StringVar()
    preset_box = ttk.Combobox(side, textvariable=preset_var, state="readonly", width=24)
    preset_box.pack(fill="x", pady=2)

    def refresh_presets():
        preset_box["values"] = sorted(state["presets"])

    def save_preset():
        name = simpledialog.askstring("Kronos Plus", "Preset name (saves the mods that are on now):")
        if name:
            state["presets"][name] = enabled_mods()
            save_state(state)
            refresh_presets()
            preset_var.set(name)

    def load_preset():
        name = preset_var.get()
        if name in state["presets"]:
            record_history(state, f"Applied preset {name}")
            apply_enabled_set(state["presets"][name])
            refresh_mods()

    def delete_preset():
        name = preset_var.get()
        if name in state["presets"] and messagebox.askyesno("Kronos Plus", f"Delete preset '{name}'?"):
            del state["presets"][name]
            save_state(state)
            preset_var.set("")
            refresh_presets()

    for text, cmd in (("Apply preset", load_preset), ("Save current as preset…", save_preset),
                      ("Delete preset", delete_preset)):
        ttk.Button(side, text=text, command=cmd).pack(fill="x", pady=2)
    ttk.Separator(side).pack(fill="x", pady=8)
    ttk.Label(side, text="Share").pack(anchor="w")
    ttk.Button(side, text="Export mod pack (.zip)…", command=export_ui).pack(fill="x", pady=2)
    ttk.Button(side, text="Install mod pack…", command=import_pack_ui).pack(fill="x", pady=2)
    ttk.Label(side, text="Double-click a mod to toggle it.\nChanges apply next game start.\nⓟ = prepared (precompiled) mod",
              style="Muted.TLabel").pack(anchor="w", pady=(10, 0))

    # ================================================================ Troubleshoot tab
    tr_tab = ttk.Frame(nb, padding=14)
    nb.add(tr_tab, text="Troubleshoot")

    sm = ttk.LabelFrame(tr_tab, text="Safe mode", padding=10)
    sm.pack(fill="x")
    ttk.Label(sm, text="Game won't start or keeps crashing? Turn every mod off in one click, then put them all back later.",
              wraplength=800).pack(anchor="w")
    smb = ttk.Frame(sm)
    smb.pack(anchor="w", pady=(6, 0))

    def safe_on():
        if state.get("safe_mode_saved") is not None:
            messagebox.showinfo("Kronos Plus", "Safe mode is already on.")
            return
        record_history(state, "Safe mode on")
        safe_mode_on(state)
        refresh_mods()

    def safe_off():
        if state.get("safe_mode_saved") is None:
            messagebox.showinfo("Kronos Plus", "Safe mode isn't on.")
            return
        safe_mode_off(state)
        refresh_mods()

    ttk.Button(smb, text="Turn safe mode on", command=safe_on).pack(side="left")
    ttk.Button(smb, text="Turn safe mode off (restore mods)", command=safe_off).pack(side="left", padx=6)

    bs = ttk.LabelFrame(tr_tab, text="Find the crashing mod", padding=10)
    bs.pack(fill="x", pady=12)
    bisect_var = tk.StringVar()
    ttk.Label(bs, text="Turns half your mods off at a time. Play a match after each step and say whether it crashed. "
                       "With 8 mods it takes about 3 tries.", wraplength=800).pack(anchor="w")
    ttk.Label(bs, textvariable=bisect_var, font=("Segoe UI", 10, "bold"), wraplength=800).pack(anchor="w", pady=6)
    bsb = ttk.Frame(bs)
    bsb.pack(anchor="w")

    def refresh_bisect():
        b = state.get("bisect")
        if b:
            bisect_var.set(f"Round {b['round']}: now testing with ONLY these on → {', '.join(b['testing'])}. "
                           "Play a match, then answer below.")
        else:
            bisect_var.set("Not running.")
        refresh_banner()

    def b_start():
        if state.get("bisect"):
            return
        err = bisect_start(state)
        if err:
            messagebox.showinfo("Kronos Plus", err)
        refresh_mods()
        refresh_bisect()

    def b_answer(crashed):
        if not state.get("bisect"):
            return
        culprit = bisect_answer(state, crashed)
        refresh_mods()
        refresh_bisect()
        if culprit:
            messagebox.showinfo("Found it", f"Most likely culprit: {culprit}\n\nYour original mods have been turned back on. "
                                            "Turn that one off on the Mods tab.")

    def b_cancel():
        bisect_cancel(state)
        refresh_mods()
        refresh_bisect()

    for text, cmd in (("Start", b_start), ("It crashed", lambda: b_answer(True)),
                      ("No crash", lambda: b_answer(False)), ("Cancel & restore", b_cancel)):
        ttk.Button(bsb, text=text, command=cmd).pack(side="left", padx=(0, 6))

    hi = ttk.LabelFrame(tr_tab, text="Undo history", padding=10)
    hi.pack(fill="both", expand=True)
    hist_list = plain(tk.Listbox(hi, height=6))
    hist_list.pack(fill="both", expand=True)

    def refresh_history():
        hist_list.delete(0, "end")
        for h in reversed(state["history"]):
            hist_list.insert("end", f"{h['time']}  {h['action']}")

    ttk.Button(hi, text="Undo most recent", command=lambda: (undo(), refresh_history())).pack(anchor="w", pady=(6, 0))

    # ================================================================ Sessions tab
    se_tab = ttk.Frame(nb, padding=10)
    nb.add(se_tab, text="Play history")
    session_status = tk.StringVar()
    ttk.Label(se_tab, textvariable=session_status, font=("Segoe UI", 10, "bold")).pack(anchor="w")
    ttk.Label(se_tab, text="Kronos Plus logs each game you play while it's open: when, how long, which mods were on, "
                           "and whether Kronos recorded a crash.", style="Muted.TLabel", wraplength=900).pack(anchor="w", pady=(2, 6))
    sess_tree = ttk.Treeview(se_tab, columns=("when", "mins", "crash", "mods"), show="headings", height=10)
    for c, w, label in (("when", 130, "Started"), ("mins", 70, "Minutes"), ("crash", 70, "Crash"), ("mods", 600, "Mods on")):
        sess_tree.heading(c, text=label)
        sess_tree.column(c, width=w, stretch=(c == "mods"))
    sess_tree.pack(fill="both", expand=True)
    suspects_var = tk.StringVar()
    ttk.Label(se_tab, textvariable=suspects_var, wraplength=900).pack(anchor="w", pady=(8, 0))

    def refresh_sessions():
        sess_tree.delete(*sess_tree.get_children())
        for s in reversed(state["sessions"]):
            sess_tree.insert("", "end", values=(s["start"], s["minutes"], "yes" if s["crash"] else "", ", ".join(s["mods"])))
        total = sum(s["minutes"] for s in state["sessions"])
        sus = crash_suspects(state)
        suspects_var.set(
            f"Total: {len(state['sessions'])} sessions, {total // 60} h {total % 60} min. " +
            ("Mods most often on when it crashed: " + ", ".join(f"{m} ({r:.0%} of {t})" for m, r, t in sus[:4])
             if sus else "No crashes recorded."))

    def poll_sessions():
        result = tracker.poll()
        session_status.set({"playing": "● Playing now (Kronos)", "idle": "Not playing", "ended": "Session saved"}[result])
        if result == "ended":
            refresh_sessions()
            refresh_logs()
        root.after(10000, poll_sessions)

    # ================================================================ Settings tab
    set_tab = ttk.Frame(nb, padding=12)
    nb.add(set_tab, text="Settings")
    flag_vars, text_vars = {}, {}
    for i, (label, path, invert) in enumerate(SETTING_FLAGS):
        v = tk.BooleanVar()
        flag_vars[path] = (v, invert)
        ttk.Checkbutton(set_tab, text=label, variable=v).grid(row=i, column=0, sticky="w", pady=2)
    for j, (label, path) in enumerate(SETTING_TEXTS):
        v = tk.StringVar()
        text_vars[path] = v
        ttk.Label(set_tab, text=label).grid(row=j, column=1, sticky="w", padx=(40, 8), pady=2)
        ttk.Entry(set_tab, textvariable=v, width=24).grid(row=j, column=2, sticky="w", pady=2)

    def load_settings_ui():
        try:
            data = load_settings()
        except (OSError, ValueError) as e:
            messagebox.showerror("Kronos Plus", f"Couldn't read settings.json:\n{e}")
            return
        for path, (v, invert) in flag_vars.items():
            val = bool(get_path(data, path, False))
            v.set(not val if invert else val)
        for path, v in text_vars.items():
            v.set(str(get_path(data, path, "")))

    def save_settings_ui():
        try:
            data = load_settings()
        except (OSError, ValueError) as e:
            messagebox.showerror("Kronos Plus", f"Couldn't read settings.json:\n{e}")
            return
        for path, (v, invert) in flag_vars.items():
            set_path(data, path, (not v.get()) if invert else v.get())
        for path, v in text_vars.items():
            set_path(data, path, v.get())
        save_settings(data)
        messagebox.showinfo("Kronos Plus", "Saved. A backup of the old settings was kept.\nRestart the game to apply.")

    def restore_ui():
        backups = list_backups()
        if not backups:
            messagebox.showinfo("Kronos Plus", "No backups yet. One is made every time you save.")
            return
        win = tk.Toplevel(root)
        win.title("Restore settings")
        lb = plain(tk.Listbox(win, width=40, height=12))
        lb.pack(padx=10, pady=10)
        apply_theme()
        for b in backups:
            lb.insert("end", b)

        def go():
            if lb.curselection():
                restore_settings(backups[lb.curselection()[0]])
                load_settings_ui()
                win.destroy()
                messagebox.showinfo("Kronos Plus", "Restored. Your settings before the restore were backed up too.")

        ttk.Button(win, text="Restore selected", command=go).pack(pady=(0, 10))

    btns = ttk.Frame(set_tab)
    btns.grid(row=len(SETTING_FLAGS) + 1, column=0, columnspan=3, sticky="w", pady=(16, 0))
    ttk.Button(btns, text="Save", command=save_settings_ui).pack(side="left")
    ttk.Button(btns, text="Reload", command=load_settings_ui).pack(side="left", padx=6)
    ttk.Button(btns, text="Restore a backup…", command=restore_ui).pack(side="left")

    # ================================================================ Logs tab
    log_tab = ttk.Frame(nb, padding=8)
    nb.add(log_tab, text="Logs")
    only_hits = tk.BooleanVar()
    log_bar = ttk.Frame(log_tab)
    log_bar.pack(side="top", fill="x", pady=(0, 6))
    log_list = plain(tk.Listbox(log_tab, width=32))
    log_list.pack(side="left", fill="y")
    log_text = plain(tk.Text(log_tab, wrap="none", font=("Consolas", 9)))
    log_text.pack(side="left", fill="both", expand=True, padx=(8, 0))
    log_files = []

    def refresh_logs():
        log_files[:] = list_logs()
        log_list.delete(0, "end")
        for p in log_files:
            log_list.insert("end", os.path.basename(p))
        if not log_files:
            log_text.delete("1.0", "end")
            log_text.insert("end", "No logs yet. They appear in kronos\\Logs after you play a match.")

    def show_log(_=None):
        if not log_list.curselection():
            return
        content = read_log(log_files[log_list.curselection()[0]])
        log_text.delete("1.0", "end")
        for line in content.splitlines():
            hit = bool(LOG_HIGHLIGHT.search(line))
            if only_hits.get() and not hit:
                continue
            log_text.insert("end", line + "\n", ("hit",) if hit else ())

    log_list.bind("<<ListboxSelect>>", show_log)
    ttk.Button(log_bar, text="Refresh", command=refresh_logs).pack(side="left")
    ttk.Checkbutton(log_bar, text="Only errors / script lines", variable=only_hits, command=show_log).pack(side="left", padx=10)

    # ================================================================ Health tab
    health_tab = ttk.Frame(nb, padding=12)
    nb.add(health_tab, text="Health check")
    health_body = ttk.Frame(health_tab)
    health_body.pack(fill="both", expand=True)

    def run_health():
        for w in health_body.winfo_children():
            w.destroy()
        for i, (ok, title, detail_text) in enumerate(health_checks(state)):
            mark, color = {True: ("✔", "#2e9d4f"), False: ("✖", "#d84343"), None: ("?", "#c08a1e")}[ok]
            ttk.Label(health_body, text=mark, foreground=color, font=("Segoe UI", 12, "bold")).grid(row=i, column=0, sticky="nw", pady=4)
            ttk.Label(health_body, text=title, font=("Segoe UI", 10, "bold")).grid(row=i, column=1, sticky="nw", padx=8, pady=4)
            ttk.Label(health_body, text=detail_text, wraplength=560).grid(row=i, column=2, sticky="nw", pady=4)
        refresh_banner()

    def mark_update_handled():
        state["last_buildid"] = steam_buildid()
        save_state(state)
        run_health()

    hb = ttk.Frame(health_tab)
    hb.pack(fill="x", pady=(10, 0))
    ttk.Button(hb, text="Run checks", command=run_health).pack(side="left")
    ttk.Button(hb, text="Mark update as handled", command=mark_update_handled).pack(side="left", padx=6)

    nb.bind("<<NotebookTabChanged>>", lambda e: (refresh_history(), refresh_bisect()))
    apply_theme()
    refresh_mods()
    refresh_bisect()
    refresh_history()
    refresh_sessions()
    load_settings_ui()
    refresh_logs()
    root.after(300, run_health)
    root.after(1000, poll_sessions)
    root.mainloop()


# ---------------------------------------------------------------- self-test

def selftest():
    state = load_state()
    print("game dir:    ", game_dir())
    print("scripts dir: ", scripts_dir())
    print("mods:")
    for name, enabled, desc in list_mods():
        print(f"   [{'on ' if enabled else 'off'}]{' (prepared)' if is_prepared(name) else ''} {name}")
    print("compile checks:")
    for name in enabled_mods():
        ok, msg = compile_check(name)
        print(f"   {({True: 'OK ', False: 'BAD', None: '-- '})[ok]} {name}: {msg.splitlines()[0] if msg else ''}")
    print("conflicts:", find_conflicts() or "none")
    print("logs:", [os.path.basename(p) for p in list_logs()] or "none yet")
    print("game running now:", SessionTracker(state).poll())
    print("health:")
    for ok, title, detail in health_checks(state):
        print(f"   {'OK ' if ok else ('?? ' if ok is None else 'BAD')} {title}: {detail}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        run_ui()
