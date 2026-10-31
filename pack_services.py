"""Application-facing install plans and pack operations; plans never trust UI file contents."""
from __future__ import annotations

import os
import tempfile
import threading
import uuid

from discord_posts import GUILD_ID, FORUM_IDS, parse_post_link
from pack_manager import MAX_BATCH_BYTES
from discord_downloads import DownloadWatch, matches_download


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
        self._preview_watches = {}
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
                choices = self.core.content.asset_folders_for(name) if os.path.splitext(path)[1].lower() not in self.core.content.ARCHIVE_EXTENSIONS else []
                if choices:
                    default = self.core.content.DEFAULT_FOLDERS.get(os.path.splitext(name)[1].lower())
                    folder = folder or default
                    if len(choices) > 1:
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
        mods = sorted(relative for relative in files if self.core.content.is_script_mod(relative))
        assets = sorted(relative for relative in files if relative.startswith("Assets/"))
        game = preview["game"]
        asset_count = len(assets) + sum(not item["selected"] for item in destinations)
        kind = ("mixed" if game or (mods and asset_count) else "mods" if mods else "assets" if asset_count else "empty")
        return {"token": token, "name": name, "files": mods + assets + game, "mods": mods, "assets": assets, "game_folder": self.core.game_dir(),
                "content_kind": kind, "content_page": {"mods": "mods", "assets": "assets"}.get(kind, "packs"),
                "detected_asset_count": asset_count,
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
        with self._lock:
            self._preview_watches.clear()
        for token in list(self._plans):
            self.forget(token)

    def cancel_preview(self, job):
        with self._lock:
            self._preview_watches.pop(job, None)

    def preview_download_status(self, job, post, update_id=None):
        with self._lock:
            watch = self._preview_watches.get(job)
            if watch is None:
                watch = self._preview_watches[job] = DownloadWatch([item["name"] for item in post["previews"]])
            if isinstance(watch, dict):
                return watch
            status = watch.poll()
            if status["status"] == "ready":
                try:
                    plan = self.prepare_preview(status["paths"], post, update_id)
                    result = {"status": "downloaded", "plan": plan}
                except (OSError, ValueError) as error:
                    result = {"status": "preview", "message": str(error), "choose_only": True}
                self._preview_watches[job] = result
                return result
            if status["status"] == "choose":
                return {**post, "message": status["message"], "choose_only": True}
            return post

    def prepare_preview(self, paths, post, update_id=None):
        source = source_link(post.get("post_url"))
        expected = [item["name"] for item in post.get("previews", [])]
        if not source or not paths or len(paths) > 20 or not expected:
            raise ValueError("The preview lookup has expired. Open its Discord post again.")
        copies = []
        try:
            for path in paths:
                name = next((name for name in expected if matches_download(os.path.basename(path), name)), None)
                if not name:
                    raise ValueError("Choose a downloaded file with one of the filenames shown in this Discord post.")
                if os.path.islink(path) or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
                    raise ValueError("Choose a regular downloaded file, not a link.")
                with open(path, "rb") as file:
                    data = file.read(32 * 1024 * 1024 + 1)
                if len(data) > 32 * 1024 * 1024:
                    raise ValueError("The preview file exceeds the 32 MB file limit.")
                # Preserve the author's filename when Windows adds a duplicate (1) suffix.
                copy = os.path.join(tempfile.mkdtemp(prefix=self.core.DOWNLOAD_PREFIX), name)
                copies.append(copy)
                with open(copy, "wb") as file:
                    file.write(data)
            return self.prepare(copies, source_post=source, update_id=update_id)
        except Exception:
            for path in copies:
                self.core.forget_download(path)
            raise

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
            return {**report, "mods": sum(self.core.content.is_script_mod(path) for path in installed), "assets": sum(path.startswith("Assets/") for path in installed),
                    "game": sum(self.core.content.is_game_file(path) for path in installed),
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
