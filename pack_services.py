"""Application-facing install plans and pack operations; plans never trust UI file contents."""
from __future__ import annotations

import os
import threading
import uuid

from discord_posts import GUILD_ID, FORUM_IDS, parse_post_link
from pack_manager import MAX_BATCH_BYTES


def source_link(url):
    if not url:
        return None
    post = parse_post_link(url)
    if not post or post.guild != GUILD_ID or not post.thread or (post.forum and post.forum not in FORUM_IDS):
        raise ValueError("Use a specific post link from Kronos #mods or #assets")
    return post.url


class PackServices:
    def __init__(self, core, state):
        self.core, self.state = core, state
        self._plans = {}
        self._lock = threading.RLock()

    @property
    def manager(self):
        return self.core.pack_manager()

    def snapshot(self):
        return self.manager.snapshot()

    def prepare(self, paths, folders=None, source_post=None, update_id=None, token=None):
        paths = list(paths or [])
        if not paths or len(paths) > 20:
            raise ValueError("Choose between 1 and 20 files")
        source_post = source_link(source_post)
        folders = folders or {}
        files, bad, destinations, seen = {}, [], [], {}
        names, total = [], 0
        for index, path in enumerate(paths):
            if not isinstance(path, str) or not os.path.isfile(path):
                raise ValueError("A selected file is no longer available")
            name = os.path.basename(path)
            folder = folders.get(str(index))
            if path.lower().endswith(".gsc"):
                with open(path, "rb") as file:
                    data = file.read(self.core.MAX_MOD_BYTES + 1)
                problem = self.core.check_mod_bytes(name, data)
                if problem:
                    bad.append(f"{name}: {problem}")
                    continue
                pack_name, batch, rejected = os.path.splitext(name)[0], {name: data}, []
            else:
                choices = self.core.content.asset_folders_for(name) if not path.lower().endswith(".zip") else []
                if choices:
                    default = self.core.content.DEFAULT_FOLDERS.get(os.path.splitext(name)[1].lower())
                    folder = folder or default
                    destinations.append({"index": str(index), "name": name, "folders": choices, "selected": folder})
                    if not folder:
                        names.append(os.path.splitext(name)[0])
                        continue
                    if folder not in choices:
                        raise ValueError("That asset folder is not supported for this file type")
                pack_name, batch, rejected = self.core.read_pack(path, folder)
            names.append(pack_name)
            bad.extend(rejected)
            total += sum(len(data) for data in batch.values())
            if total > MAX_BATCH_BYTES:
                raise ValueError("The selected batch exceeds the 128 MB expanded-size limit")
            for relative, data in batch.items():
                previous = seen.get(relative.casefold())
                if previous:
                    if files[previous] != data:
                        raise ValueError(f"Selected attachments contain different versions of {relative}. Choose one version.")
                    continue
                seen[relative.casefold()] = relative
                files[relative] = data
        snapshot = self.manager.snapshot()
        old_pack = next((pack for pack in snapshot["packs"] if pack["id"] == update_id), None)
        if update_id and not old_pack:
            raise ValueError("That pack is no longer installed")
        name = old_pack["name"] if old_pack else names[0] if len(paths) == 1 and names else "Batch · " + (names[0] if names else "Imported files")
        preview = self.manager.preview(files, update_id)
        token = token or uuid.uuid4().hex
        plan = {"token": token, "paths": paths, "folders": folders, "files": files, "bad": bad,
                "name": name, "source_post": source_post or (old_pack or {}).get("source_post"),
                "update_id": update_id, "attachments": [os.path.basename(path) for path in paths], "destinations": destinations}
        with self._lock:
            self._plans[token] = plan
        mods = sorted(relative for relative in files if self.core.is_source_mod(relative))
        assets = sorted(relative for relative in files if relative.startswith("Assets/"))
        return {"token": token, "name": name, "files": mods + assets, "mods": mods, "assets": assets,
                "bad": bad, "destinations": destinations, "unresolved": any(not item["selected"] for item in destinations),
                "source_post": plan["source_post"], "update_id": update_id, **preview}

    def revise(self, token, folders):
        with self._lock:
            plan = self._plans.get(token)
            if not plan:
                raise ValueError("This install review has expired; choose the files again")
            return self.prepare(plan["paths"], folders, plan["source_post"], plan["update_id"], token)

    def forget(self, token):
        with self._lock:
            plan = self._plans.pop(token, None)
        if plan:
            for path in plan["paths"]:
                self.core.forget_download(path)

    def close(self):
        for token in list(self._plans):
            self.forget(token)

    def download(self, urls, source_post=None, update_id=None):
        if not isinstance(urls, list) or not 1 <= len(urls) <= 20:
            raise ValueError("Select between 1 and 20 attachments")
        paths = []
        try:
            for url in urls:
                paths.append(self.core.download_mod_link(url))
            return self.prepare(paths, source_post=source_post, update_id=update_id)
        except Exception:
            for path in paths:
                self.core.forget_download(path)
            raise

    def install(self, token, overwrite, name, make_preset=False):
        with self._lock:
            plan = self._plans.get(token)
            if not plan:
                raise ValueError("This install review has expired; choose the files again")
            if any(not item["selected"] for item in plan["destinations"]):
                raise ValueError("Choose a destination for each asset first")
            report = self.manager.install(name or plan["name"], plan["files"], overwrite,
                plan["source_post"], plan["attachments"], plan["update_id"])
            installed = report["installed"]
            mods = [relative[:-4] for relative in installed if self.core.is_source_mod(relative)]
            metadata_warning = None
            if make_preset and mods:
                self.state["presets"][report["name"]] = mods
                try:
                    self.core.save_state(self.state)
                except OSError:
                    metadata_warning = "The pack was installed, but its source-mod preset could not be saved."
            self.forget(token)
            return {**report, "mods": len(mods), "assets": sum(path.startswith("Assets/") for path in installed),
                    "skipped": len(report["skipped"]), "warning": metadata_warning}

    def assets(self):
        snapshot = self.snapshot()
        known = {path.casefold() for path in snapshot["managed_paths"]}
        owners = {path.casefold(): value for path, value in snapshot["owners"].items()}
        items = self.core.list_assets()
        legacy = self.state.get("assets", {})
        for item in items:
            relative = "Assets/" + item["path"]
            owner = owners.get(relative.casefold())
            old = legacy.get(item["path"], {}) if relative.casefold() not in known else {}
            item["pack_id"] = owner["id"] if owner else None
            item["pack"] = owner["name"] if owner else old.get("pack")
            item["mine"] = bool(owner or old)
        return items

    def action_preview(self, identity, action):
        snapshot = self.snapshot()
        pack = next((pack for pack in snapshot["packs"] if pack["id"] == identity), None)
        if not pack or action not in {"enable", "disable", "uninstall"}:
            raise ValueError("Unknown pack action")
        conflicts = []
        for conflict in pack["conflicts"]:
            owners = [item for item in snapshot["packs"] if conflict["path"] in item["files"]]
            future = [item for item in owners if (action == "enable" if item["id"] == identity else item["enabled"])]
            conflicts.append({**conflict, "nextActive": future[-1]["name"] if future else "Original file or removed"})
        return {"pack": pack, "action": action, "files": len(pack["files"]), "modified": pack["modified"], "conflicts": conflicts}
