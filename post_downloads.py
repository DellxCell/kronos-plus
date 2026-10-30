"""Download the chosen post attachments, then prepare one normal install review."""
from __future__ import annotations

import threading
import time

from discord_downloads import DownloadWatch
from pack_services import source_link


class _Cancelled(Exception):
    pass


class AutomaticPostDownloads:
    def __init__(self, importer, services, watch_factory=DownloadWatch, timeout=45, on_ready=None):
        self.importer, self.services = importer, services
        self.watch_factory, self.timeout = watch_factory, timeout
        self._jobs = {}
        self._lock = threading.RLock()
        self._on_ready = on_ready

    def start(self, key, indices, update_id=None):
        post = self.importer.status(key)
        catalog = [dict(item, kind="link") for item in post.get("files", [])]
        catalog += [dict(item, kind="preview") for item in post.get("previews", [])]
        if (post.get("status") not in {"preview", "ready"} or not source_link(post.get("post_url"))
                or not isinstance(indices, list) or not 1 <= len(indices) <= 20
                or any(type(index) is not int or not 0 <= index < len(catalog) for index in indices)
                or len(set(indices)) != len(indices)):
            raise ValueError("Select between 1 and 20 attachments from this post.")
        selected = [catalog[index] for index in indices]
        with self._lock:
            if key in self._jobs:
                return self.status(key)
            state = {"cancel": threading.Event(), "owned": [], "plan": None, "delivered": False,
                     "post": {"post_url": post["post_url"],
                              "previews": [{k: v for k, v in item.items() if k != "kind"} for item in selected if item["kind"] == "preview"]},
                     "links": [item["url"] for item in selected if item["kind"] == "link"],
                     "update_id": update_id, "result": {"status": "downloading", "message": "Starting the attachment download…"}}
            self._jobs[key] = state
        threading.Thread(target=self._worker, args=(key, state), daemon=True).start()
        return {"status": "downloading", "message": "Starting the attachment download…"}

    def _live(self, state):
        if state["cancel"].is_set():
            raise _Cancelled()

    def _publish(self, key, state, result):
        wake = False
        with self._lock:
            if self._jobs.get(key) is not state or state["cancel"].is_set():
                if result.get("plan"):
                    self.services.forget(result["plan"]["token"])
                return
            state["result"] = result
            if result.get("plan"):
                state["plan"] = result["plan"]
                state["owned"] = []  # The immutable install plan owns these temporary files now.
                wake = True
            elif result.get("status") in {"error", "needs_file"}:
                wake = True
        if wake and self._on_ready:
            self._on_ready()

    def _assemble(self, state, preview_paths):
        self._live(state)
        token = None
        try:
            for url in state["links"]:
                self._live(state)
                path = self.services.core.download_mod_link(url)
                with self._lock:
                    state["owned"].append(path)
            self._live(state)
            if state["post"]["previews"]:
                plan = self.services.prepare_preview(preview_paths, state["post"], state["update_id"])
                token = plan["token"]
                paths = self.services._plans[token]["paths"] + list(state["owned"])
                if state["owned"]:
                    plan = self.services.prepare(paths, source_post=state["post"]["post_url"],
                                                 update_id=state["update_id"], token=token)
            else:
                plan = self.services.prepare(list(state["owned"]), source_post=state["post"]["post_url"], update_id=state["update_id"])
                token = plan["token"]
            self._live(state)
            return plan
        except Exception:
            if token:
                self.services.forget(token)
            raise

    def _worker(self, key, state):
        preview_paths = []
        try:
            previews = state["post"]["previews"]
            if previews:
                # Capture the baseline before requesting any browser download.
                watch = self.watch_factory([item["name"] for item in previews])
                try:
                    for item in previews:
                        self._live(state)
                        self._publish(key, state, {"status": "downloading", "message": "Downloading " + item["name"] + " from Discord…"})
                        result = self.importer.download_preview(key, item)
                        if result.get("status") != "requested":
                            raise ValueError(result.get("message") or result.get("reader_error") or "Discord couldn't start this attachment download.")
                    deadline = time.monotonic() + self.timeout
                    while time.monotonic() < deadline:
                        self._live(state)
                        result = watch.poll()
                        if result["status"] == "ready":
                            preview_paths = result["paths"]
                            break
                        if result["status"] == "choose":
                            raise ValueError(result["message"])
                        state["cancel"].wait(0.25)
                    else:
                        raise ValueError("Your browser hasn't saved the attachment in Downloads. Finish any Save dialog, or choose the downloaded file below.")
                except ValueError as error:
                    self._publish(key, state, {"status": "needs_file", "message": str(error), "previews": previews})
                    return
            self._live(state)
            self._publish(key, state, {"status": "downloading", "message": "Checking the downloaded files…"})
            plan = self._assemble(state, preview_paths)
            self._publish(key, state, {"status": "downloaded", "plan": plan})
        except _Cancelled:
            pass
        except Exception as error:
            self._publish(key, state, {"status": "error", "message": str(error) if isinstance(error, (ValueError, OSError)) else "The attachment download couldn't finish. Retry the post link."})
        finally:
            if state["cancel"].is_set() or state["result"].get("status") == "error":
                self._cleanup(state)

    def status(self, key):
        with self._lock:
            state = self._jobs.get(key)
            if state is None:
                return None
            if state["result"]["status"] == "downloaded":
                state["delivered"] = True
            return dict(state["result"])

    def manual(self, key, paths):
        with self._lock:
            state = self._jobs.get(key)
            if not state or state["result"]["status"] != "needs_file":
                raise ValueError("The automatic download is still in progress. Wait for it to finish.")
        plan = self._assemble(state, paths)
        # The caller takes ownership of this review immediately.
        with self._lock:
            state["owned"] = []
            state["delivered"] = True
            state["plan"] = plan
            state["result"] = {"status": "downloaded", "plan": plan}
        return plan

    def _cleanup(self, state):
        with self._lock:
            paths, state["owned"] = state["owned"], []
        for path in paths:
            self.services.core.forget_download(path)

    def cancel(self, key):
        with self._lock:
            state = self._jobs.pop(key, None)
            if not state:
                return
            state["cancel"].set()
            if state["plan"] and not state["delivered"]:
                self.services.forget(state["plan"]["token"])
        self._cleanup(state)

    def close(self):
        with self._lock:
            keys = list(self._jobs)
        for key in keys:
            self.cancel(key)
