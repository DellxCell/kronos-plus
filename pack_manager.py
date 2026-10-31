"""Shared pack library with layered ownership, originals, and atomic file transactions."""
from __future__ import annotations

import contextlib
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import threading
import uuid

import content_packs as content

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_BATCH_BYTES = 128 * 1024 * 1024
HASH = re.compile(r"[0-9a-f]{64}\Z")
IDENTITY = re.compile(r"[0-9a-f]{32}\Z")


class PhysicalPlan(dict):
    """Windows paths that differ only in casing identify one physical destination."""
    def __init__(self):
        super().__init__()
        self._actual = {}

    @staticmethod
    def key(path):
        return os.path.normcase(os.path.abspath(path))

    def __setitem__(self, path, value):
        key = self.key(path)
        actual = self._actual.setdefault(key, os.path.abspath(path))
        super().__setitem__(actual, value)

    def __getitem__(self, path):
        return super().__getitem__(self._actual[self.key(path)])

    def __contains__(self, path):
        return self.key(path) in self._actual

    def get(self, path, default=None):
        actual = self._actual.get(self.key(path))
        return super().get(actual, default)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def empty_registry():
    return {"schema": 1, "packs": {}, "order": [], "bases": {}, "source_disabled": [], "profiles": {}}


class PackManager:
    def __init__(self, scripts, assets, disabled, library, manifest_suffix=".kronos.json"):
        self.scripts, self.assets, self.disabled, self.library = map(os.path.abspath, (scripts, assets, disabled, library))
        self.manifest_suffix = manifest_suffix
        self._thread_lock = threading.RLock()
        self._index = os.path.join(self.library, "index.json")

    def _under(self, path, root):
        path, root = os.path.abspath(path), os.path.abspath(root)
        try:
            return os.path.normcase(os.path.commonpath([path, root])) == os.path.normcase(root) and path != root
        except ValueError:
            return False

    def _safe(self, path, internal=False):
        roots = (self.library,) if internal else (self.scripts, self.assets, self.disabled)
        path = os.path.abspath(path)
        root = next((root for root in roots if self._under(path, root)), None)
        if not root:
            raise ValueError("Pack destination is outside its allowed folder")
        if not self._under(os.path.realpath(path), os.path.realpath(root)):
            raise ValueError("Pack destination leaves its allowed folder")
        current = root
        for part in Path(os.path.relpath(path, root)).parts:
            current = os.path.join(current, part)
            if os.path.lexists(current):
                info = os.lstat(current)
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise ValueError("Pack destination contains a link or junction")
        return path

    def _write(self, path, data, internal=False):
        path = self._safe(path, internal)
        if data is None:
            if os.path.isfile(path):
                os.remove(path)
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._safe(path, internal)
        handle, temporary = tempfile.mkstemp(prefix=".kp-pack-", dir=os.path.dirname(path))
        try:
            with os.fdopen(handle, "wb") as file:
                file.write(data)
                file.flush()
                os.fsync(file.fileno())
            self._safe(path, internal)
            os.replace(temporary, path)
        finally:
            if os.path.isfile(temporary):
                os.remove(temporary)

    def _json(self, path, data):
        self._write(path, json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"), internal=True)

    def _blob_path(self, digest):
        if not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise ValueError("Invalid pack object identifier")
        return self._safe(os.path.join(self.library, "objects", digest[:2], digest), internal=True)

    def _put(self, data):
        digest = hashlib.sha256(data).hexdigest()
        path = self._blob_path(digest)
        if not os.path.isfile(path):
            self._write(path, data, internal=True)
        return digest

    def _get(self, digest):
        if digest is None:
            return None
        with open(self._blob_path(digest), "rb") as file:
            data = file.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("A stored pack file is damaged; no game files were changed")
        return data

    def _file_hash(self, path, store=False):
        self._safe(path)
        if not os.path.exists(path):
            return None
        if not os.path.isfile(path):
            raise ValueError("A pack file destination is a folder")
        with open(path, "rb") as file:
            data = file.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("An existing file exceeds the pack manager's 64 MB file limit")
        return self._put(data) if store else hashlib.sha256(data).hexdigest()

    def _locations(self, relative):
        active = content.destination_for(relative, self.scripts, self.assets, self.manifest_suffix)
        self._safe(active)
        if relative.startswith("Assets/"):
            return {"active": active}
        disabled = content.destination_for(relative, self.disabled, self.assets, self.manifest_suffix)
        self._safe(disabled)
        return {"active": active, "disabled": disabled}

    def _live(self, relative, store=False):
        return {slot: self._file_hash(path, store) for slot, path in self._locations(relative).items()}

    def _mod_name(self, relative):
        return relative[:-len(self.manifest_suffix)] if relative.lower().endswith(self.manifest_suffix) else os.path.splitext(relative)[0]

    def _read(self):
        if not os.path.isfile(self._index):
            return empty_registry()
        with open(self._safe(self._index, True), encoding="utf-8") as file:
            data = json.load(file)
        if (not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("packs"), dict)
                or not isinstance(data.get("bases"), dict) or not isinstance(data.get("order"), list)
                or not isinstance(data.get("profiles"), dict) or not isinstance(data.get("source_disabled"), list)):
            raise ValueError("The pack library index is invalid; it was left unchanged")
        if set(data["order"]) != set(data["packs"]) or len(data["order"]) != len(data["packs"]):
            raise ValueError("The pack priority list is invalid")
        for identity, pack in data["packs"].items():
            if not IDENTITY.fullmatch(identity) or not isinstance(pack, dict) or not isinstance(pack.get("files"), dict):
                raise ValueError("Invalid pack record")
            for relative, digest in pack["files"].items():
                self._locations(relative)
                self._blob_path(digest)
                if relative not in data["bases"]:
                    raise ValueError("A pack is missing its original-file record")
        for relative, snapshot in data["bases"].items():
            locations = self._locations(relative)
            if not isinstance(snapshot, dict) or set(snapshot) != set(locations):
                raise ValueError("Invalid original-file record")
            for digest in snapshot.values():
                if digest is not None:
                    self._blob_path(digest)
        return data

    @contextlib.contextmanager
    def _locked(self):
        with self._thread_lock:
            os.makedirs(self.library, exist_ok=True)
            lock_path = self._safe(os.path.join(self.library, "library.lock"), True)
            with open(lock_path, "a+b") as lock:
                lock.seek(0, os.SEEK_END)
                if not lock.tell():
                    lock.write(b"0")
                    lock.flush()
                lock.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise ValueError("Another Kronos Plus window is changing packs. Try again in a moment.") from None
                try:
                    self._recover()
                    yield
                finally:
                    lock.seek(0)
                    if os.name == "nt":
                        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def locked(self):
        """Hold the library lock so nothing else changes packs, e.g. while a full backup is made or restored."""
        return self._locked()

    def _recover(self):
        folder = os.path.join(self.library, "transactions")
        if not os.path.isdir(folder):
            return
        for name in os.listdir(folder):
            if not re.fullmatch(r"[0-9a-f]{32}\.json", name):
                continue
            path = self._safe(os.path.join(folder, name), True)
            with open(path, encoding="utf-8") as file:
                journal = json.load(file)
            if journal.get("status") != "pending":
                continue
            registry = self._read()
            operations = journal["operations"]
            for operation in operations:
                self._safe(operation["path"])
                for digest in (operation["before"], operation["after"]):
                    if digest:
                        self._get(digest)
            if registry == journal["after_registry"] and all(self._file_hash(op["path"]) == op["after"] for op in operations):
                journal["status"] = "committed"
                self._json(path, journal)
                continue
            if registry != journal["before_registry"]:
                raise ValueError("An interrupted pack operation needs recovery. Its saved files are in " + folder)
            if any(self._file_hash(op["path"]) not in (op["before"], op["after"]) for op in operations):
                raise ValueError("Files changed after an interrupted pack operation. Recovery copies are in " + folder)
            for operation in reversed(operations):
                self._write(operation["path"], self._get(operation["before"]))
            journal["status"] = "rolled_back"
            self._json(path, journal)

    def _compose(self, registry):
        result = copy.deepcopy(registry["bases"])
        disabled = set(registry["source_disabled"])
        for identity in registry["order"]:
            pack = registry["packs"][identity]
            if not pack["enabled"]:
                continue
            for relative, digest in pack["files"].items():
                if relative.startswith("Assets/"):
                    result[relative] = {"active": digest}
                else:
                    off = self._mod_name(relative).casefold() in disabled
                    result[relative] = {"active": None if off else digest, "disabled": digest if off else None}
        return result

    def _owners(self, registry, relative):
        return [identity for identity in registry["order"] if relative in registry["packs"][identity]["files"]]

    def _winner(self, registry, relative):
        return next((identity for identity in reversed(self._owners(registry, relative)) if registry["packs"][identity]["enabled"]), None)

    def _canonical(self, registry, files):
        known = {relative.casefold(): relative for relative in registry["bases"]}
        output, seen = {}, set()
        if sum(len(data) for data in files.values()) > MAX_BATCH_BYTES:
            raise ValueError("The selected batch exceeds the 128 MB expanded-size limit")
        for relative, data in files.items():
            self._locations(relative)
            key = relative.casefold()
            if key in seen:
                raise ValueError("Two selected files have the same destination")
            seen.add(key)
            relative = known.get(key, relative)
            if relative.startswith("Assets/"):
                content.validate_asset(relative, data)
            elif relative.lower().endswith(".gscc"):
                content.validate_compiled(data)
            elif relative.lower().endswith(".gsc"):
                if len(data) > content.MAX_SOURCE_BYTES or b"\x00" in data or data.startswith(b"MZ"):
                    raise ValueError("Invalid source script")
                data.decode("utf-8-sig")
            else:
                if len(data) > content.MAX_SOURCE_BYTES or not isinstance(json.loads(data.decode("utf-8-sig")), dict):
                    raise ValueError("Invalid source manifest")
            output[relative] = data
        return output

    def _script_files(self, extra=()):
        """{casefolded name: (name, main file)} for every mod: its .gsc, or its .gscc when it comes only compiled."""
        found = {".gsc": {}, ".gscc": {}}
        roots = {os.path.normcase(self.scripts), os.path.normcase(self.disabled)}
        files = [os.path.join(root, f) for root in (self.scripts, self.disabled) if os.path.isdir(root)
                 for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]
        for path in [*files, *extra]:
            stem, extension = os.path.splitext(os.path.basename(path))
            if os.path.normcase(os.path.dirname(path)) in roots and extension.lower() in found:
                found[extension.lower()].setdefault(stem.casefold(), stem)
        names = {key: (stem, stem + ".gscc") for key, stem in found[".gscc"].items() if key not in found[".gsc"]}
        names.update((key, (stem, stem + ".gsc")) for key, stem in found[".gsc"].items())
        return names

    def _project_sources(self, operations, enabled_names, only=None):
        enabled = {name.casefold() for name in enabled_names}
        names = self._script_files(operations)
        if only is not None:
            names = {key: name for key, name in names.items() if key in {item.casefold() for item in only}}
        for name, main in names.values():
            content.safe_parts(main)
            source_paths = [os.path.join(root, main) for root in (self.scripts, self.disabled)]
            values = [operations[path] if path in operations else self._file_hash(path, True) for path in source_paths]
            if sum(value is not None for value in values) > 1:
                raise ValueError(f"{main} exists in both enabled and disabled folders; resolve that duplicate first")
            digest = next((value for value in values if value is not None), None)
            if digest is None:
                continue
            target_root = self.scripts if name.casefold() in enabled else self.disabled
            operations[source_paths[0]] = digest if target_root == self.scripts else None
            operations[source_paths[1]] = digest if target_root == self.disabled else None
            companions = set()
            for root in (self.scripts, self.disabled):
                if os.path.isdir(root):
                    companions.update(filename for filename in os.listdir(root) if filename.startswith(name + ".")
                                      and filename != main and os.path.isfile(os.path.join(root, filename)))
            companions.add("compiled/" + name + ".gscc")
            for filename in companions:
                content.safe_parts(filename)
                paths = [os.path.join(root, *filename.split("/")) for root in (self.scripts, self.disabled)]
                hashes = [operations[path] if path in operations else self._file_hash(path, True) for path in paths]
                existing = [(i, value) for i, value in enumerate(hashes) if value is not None]
                if not existing:
                    continue
                if len(existing) > 1 and hashes[0] != hashes[1]:
                    raise ValueError(f"Conflicting companion files for {name}; resolve the duplicate first")
                value = existing[0][1]
                operations[paths[0]] = value if target_root == self.scripts else None
                operations[paths[1]] = value if target_root == self.disabled else None

    def _operations(self, before, after, affected, profile_mods=None, only_mods=None):
        old, new = self._compose(before), self._compose(after)
        operations, edited = PhysicalPlan(), []
        for relative in sorted(affected):
            locations = self._locations(relative)
            live = self._live(relative, True)
            desired = new.get(relative, {slot: None for slot in locations})
            expected = old.get(relative, live)
            if live != expected:
                edited.append(relative)
            for slot, path in locations.items():
                operations[path] = desired.get(slot)
            if relative.lower().endswith(".gsc") and not relative.startswith("Assets/"):
                previous = next((digest for digest in live.values() if digest), None)
                following = next((digest for digest in desired.values() if digest), None)
                if previous != following:
                    for root in (self.scripts, self.disabled):
                        cache = self._safe(os.path.join(root, "compiled", relative[:-4] + ".gscc"))
                        operations[cache] = None
        if profile_mods is not None:
            self._project_sources(operations, profile_mods, only_mods)
        # Moving a managed source between folders also moves its generated cache.
        elif any(not relative.startswith("Assets/") for relative in affected):
            enabled = self.enabled_mods()
            for relative in affected:
                if relative.lower().endswith((".gsc", ".gscc")) and not relative.startswith("Assets/"):
                    name = self._mod_name(relative)
                    active = operations.get(os.path.join(self.scripts, relative))
                    enabled = [item for item in enabled if item.casefold() != name.casefold()]
                    if active:
                        enabled.append(name)
            self._project_sources(operations, enabled, {self._mod_name(r) for r in affected if not r.startswith("Assets/")})
        return operations, edited

    def _commit(self, before, after, operations, action, edited=()):
        changes = []
        for path, digest in operations.items():
            current = self._file_hash(path, True)
            self._get(digest)  # Validate every stored object before changing any live file.
            if current != digest:
                changes.append({"path": path, "before": current, "after": digest})
        identity = uuid.uuid4().hex
        journal_path = self._safe(os.path.join(self.library, "transactions", identity + ".json"), True)
        journal = {"status": "pending", "action": action, "time": now(), "operations": changes,
                   "before_registry": before, "after_registry": after, "edited_files": list(edited)}
        recovery_folder = None
        if edited:
            for relative in edited:
                for slot, path in self._locations(relative).items():
                    digest = self._file_hash(path, True)
                    if digest:
                        prefix = "Assets" if relative.startswith("Assets/") else "custom_scripts" if slot == "active" else "custom_scripts_disabled"
                        leaf = relative[len("Assets/"):] if relative.startswith("Assets/") else relative
                        saved = self._safe(os.path.join(self.library, "recovery", identity, prefix, *leaf.split("/")), True)
                        self._write(saved, self._get(digest), internal=True)
                        recovery_folder = os.path.join(self.library, "recovery", identity)
        journal["recovery_folder"] = recovery_folder
        self._json(journal_path, journal)
        written = []
        try:
            for change in changes:
                if self._file_hash(change["path"]) != change["before"]:
                    raise ValueError("A file changed during the operation; retry after closing its editor")
                self._write(change["path"], self._get(change["after"]))
                written.append(change)
            self._json(self._index, after)
        except Exception:
            for change in reversed(written):
                self._write(change["path"], self._get(change["before"]))
            journal["status"] = "rolled_back"
            self._json(journal_path, journal)
            raise
        journal["status"] = "committed"
        try:
            self._json(journal_path, journal)
        except OSError:
            pass  # The committed index lets startup recovery finish this marker.
        return {"changed": len(changes), "recovery": recovery_folder,
                "edited": list(edited), "backup": journal_path if any(item["before"] for item in changes) else None}

    def enabled_mods(self):
        return [name for name, main in self._script_files().values() if os.path.isfile(os.path.join(self.scripts, main))]

    def preview(self, files, update_id=None):
        with self._locked():
            registry = self._read()
            if update_id and update_id not in registry["packs"]:
                raise ValueError("That pack is no longer installed")
            files = self._canonical(registry, files)
            old_files = registry["packs"].get(update_id, {}).get("files", {})
            conflicts, existing = [], []
            for relative, data in files.items():
                live = self._live(relative)
                owners = self._owners(registry, relative)
                identical = hashlib.sha256(data).hexdigest() in live.values()
                needs_replace = any(live.values()) and relative not in old_files and not identical
                if needs_replace:
                    existing.append(relative)
                if owners or needs_replace:
                    winner = self._winner(registry, relative)
                    conflicts.append({"path": relative, "owners": [registry["packs"][key]["name"] for key in owners],
                                      "active": registry["packs"][winner]["name"] if winner else "Existing file",
                                      "replace": needs_replace, "same": identical})
            return {"existing": existing, "conflicts": conflicts, "removed": sorted(set(old_files) - set(files))}

    def install(self, name, files, overwrite=(), source_post=None, attachments=(), update_id=None):
        name = str(name or "Imported pack").strip()[:120]
        if not name:
            raise ValueError("Give this pack a name")
        with self._locked():
            before = self._read()
            if update_id and update_id not in before["packs"]:
                raise ValueError("That pack is no longer installed")
            files = self._canonical(before, files)
            old_pack = before["packs"].get(update_id)
            old_files = old_pack["files"] if old_pack else {}
            overwrite = {item.casefold() for item in overwrite}
            selected, skipped = {}, []
            for relative, data in files.items():
                live = self._live(relative)
                same = hashlib.sha256(data).hexdigest() in live.values()
                if any(live.values()) and relative not in old_files and relative.casefold() not in overwrite and not same:
                    skipped.append(relative)
                    continue
                if relative.lower().endswith(".gsc") and not relative.startswith("Assets/") and relative not in before["bases"]:
                    for root in (self.scripts, self.disabled):
                        if os.path.isfile(os.path.join(root, relative[:-4] + ".gscc")):
                            raise ValueError(f"{relative} belongs to a prepared mod; it cannot be replaced by a source-only pack")
                selected[relative] = self._put(data)
            for relative in list(selected):
                if relative.lower().endswith(self.manifest_suffix) and not relative.startswith("Assets/"):
                    source = relative[:-len(self.manifest_suffix)] + ".gsc"
                    if source.casefold() not in {key.casefold() for key in selected}:
                        del selected[relative]
                        skipped.append(relative)
            if not selected:
                raise ValueError("No files selected for installation; existing files were left unchanged")
            after = copy.deepcopy(before)
            identity = update_id or uuid.uuid4().hex
            for relative in selected:
                if relative not in after["bases"]:
                    after["bases"][relative] = self._live(relative, True)
            after["packs"][identity] = {"id": identity, "name": name, "enabled": old_pack["enabled"] if old_pack else True,
                "files": selected, "source_post": source_post if source_post is not None else (old_pack or {}).get("source_post"),
                "attachments": list(attachments)[:20], "installed": (old_pack or {}).get("installed", now()), "updated": now()}
            if not old_pack:
                after["order"].append(identity)
                new_mods = {self._mod_name(relative).casefold() for relative in selected if not relative.startswith("Assets/")}
                after["source_disabled"] = [name for name in after["source_disabled"] if name not in new_mods]
            affected = set(selected) | set(old_files)
            operations, edited = self._operations(before, after, affected)
            self._drop_unused_bases(after)
            report = self._commit(before, after, operations, "Update pack" if old_pack else "Install pack", edited)
            report.update({"id": identity, "name": name, "installed": list(selected), "skipped": skipped,
                           "removed": sorted(set(old_files) - set(selected))})
            return report

    def _drop_unused_bases(self, registry):
        used = {relative for pack in registry["packs"].values() for relative in pack["files"]}
        registry["bases"] = {relative: snapshot for relative, snapshot in registry["bases"].items() if relative in used}

    def change(self, identity, action):
        with self._locked():
            before = self._read()
            if identity not in before["packs"] or action not in {"enable", "disable", "uninstall"}:
                raise ValueError("Unknown pack action")
            after = copy.deepcopy(before)
            affected = set(before["packs"][identity]["files"])
            if action == "uninstall":
                del after["packs"][identity]
                after["order"].remove(identity)
            else:
                after["packs"][identity]["enabled"] = action == "enable"
            operations, edited = self._operations(before, after, affected)
            self._drop_unused_bases(after)
            return self._commit(before, after, operations, action.capitalize() + " pack", edited)

    def set_mods(self, names, enabled):
        with self._locked():
            before = self._read()
            after = copy.deepcopy(before)
            selected = {name.casefold() for name in names}
            disabled = set(after["source_disabled"])
            disabled = disabled - selected if enabled else disabled | selected
            after["source_disabled"] = sorted(disabled)
            affected = {relative for relative in before["bases"] if not relative.startswith("Assets/") and self._mod_name(relative).casefold() in selected}
            mods = set(self.enabled_mods())
            mods = mods | set(names) if enabled else {name for name in mods if name.casefold() not in selected}
            operations, edited = self._operations(before, after, affected, mods, names)
            return self._commit(before, after, operations, "Change source mods", edited)

    def set_all_mods(self, names):
        with self._locked():
            before = self._read()
            after = copy.deepcopy(before)
            all_names = {self._mod_name(relative).casefold() for relative in before["bases"] if not relative.startswith("Assets/")}
            after["source_disabled"] = sorted(all_names - {name.casefold() for name in names})
            operations, edited = self._operations(before, after, {r for r in before["bases"] if not r.startswith("Assets/")}, names)
            return self._commit(before, after, operations, "Apply source mods", edited)

    def save_profile(self, name):
        name = str(name or "").strip()[:120]
        if not name:
            raise ValueError("Give this profile a name")
        with self._locked():
            before = self._read()
            after = copy.deepcopy(before)
            after["profiles"][name] = {"packs": [key for key in before["order"] if before["packs"][key]["enabled"]],
                "order": list(before["order"]), "mods": self.enabled_mods(), "saved": now()}
            self._commit(before, after, {}, "Save profile")
            return name

    def apply_profile(self, name):
        with self._locked():
            before = self._read()
            profile = before["profiles"].get(name)
            if not profile:
                raise ValueError("That profile no longer exists")
            if any(identity not in before["packs"] for identity in profile["packs"]):
                raise ValueError("This profile includes an uninstalled pack; reinstall the required pack and save a new profile")
            after = copy.deepcopy(before)
            for identity, pack in after["packs"].items():
                pack["enabled"] = identity in profile["packs"]
            order = [key for key in profile["order"] if key in after["packs"]]
            after["order"] = order + [key for key in after["order"] if key not in order]
            managed_mods = {self._mod_name(relative).casefold() for relative in before["bases"] if not relative.startswith("Assets/")}
            after["source_disabled"] = sorted(managed_mods - {name.casefold() for name in profile["mods"]})
            operations, edited = self._operations(before, after, set(before["bases"]), profile["mods"])
            return self._commit(before, after, operations, "Apply profile", edited)

    def delete_profile(self, name):
        with self._locked():
            before = self._read()
            after = copy.deepcopy(before)
            after["profiles"].pop(name, None)
            self._commit(before, after, {}, "Delete profile")

    def set_source(self, identity, source_post):
        with self._locked():
            before = self._read()
            after = copy.deepcopy(before)
            if identity not in after["packs"]:
                raise ValueError("That pack no longer exists")
            after["packs"][identity]["source_post"] = source_post
            self._commit(before, after, {}, "Set pack source")

    def snapshot(self):
        with self._locked():
            registry = self._read()
            expected = self._compose(registry)
            packs = []
            active_owners = {}
            for relative in registry["bases"]:
                winner = self._winner(registry, relative)
                if winner:
                    pack = registry["packs"][winner]
                    active_owners[relative] = {"id": winner, "name": pack["name"]}
            for identity in registry["order"]:
                pack = registry["packs"][identity]
                modified, conflicts = [], []
                for relative in pack["files"]:
                    if self._live(relative) != expected[relative]:
                        modified.append(relative)
                    owners = self._owners(registry, relative)
                    if len(owners) > 1:
                        winner = self._winner(registry, relative)
                        conflicts.append({"path": relative, "packs": [registry["packs"][key]["name"] for key in owners],
                                          "active": registry["packs"][winner]["name"] if winner else "Original file"})
                packs.append({key: value for key, value in pack.items() if key != "files"} | {
                    "files": sorted(pack["files"]), "assets": sum(key.startswith("Assets/") for key in pack["files"]),
                    "mods": sum(content.is_script_mod(key) for key in pack["files"]),
                    "conflicts": conflicts, "modified": modified})
            return {"packs": packs, "profiles": registry["profiles"], "owners": active_owners,
                    "managed_paths": list(registry["bases"]), "library": self.library}
