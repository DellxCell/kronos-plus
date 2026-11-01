"""Serves asset images to the window from localhost, so thumbnails load as plain image files
instead of travelling through the pywebview bridge as base64 text."""
import http.server
import os
import secrets
import threading
import urllib.parse

MAX_IMAGE_BYTES = 4 * 1024 * 1024


class AssetServer:
    def __init__(self, resolve, types):
        # resolve(rel) gives the file's full path inside Assets or raises ValueError; types maps extension to MIME type.
        self._resolve, self._types = resolve, types
        self._token = secrets.token_urlsafe(18)
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                owner._serve(self)

            def log_message(self, *args):
                pass

        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._httpd.daemon_threads = True
        self._host = f"127.0.0.1:{self._httpd.server_address[1]}"
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def url(self, rel, info):
        """The link changes whenever the file does, so the window can cache each version for good."""
        return f"http://{self._host}/{self._token}/{urllib.parse.quote(rel)}?v={info.st_mtime_ns:x}-{info.st_size:x}"

    def _serve(self, request):
        path, prefix = urllib.parse.urlsplit(request.path).path, f"/{self._token}/"
        # Only links this app made: the secret token, and our exact host so a rebinding web page can't reach it.
        if request.headers.get("Host") != self._host or not path.startswith(prefix):
            return request.send_error(404)
        try:
            file = self._resolve(urllib.parse.unquote(path[len(prefix):]))
            mime = self._types[os.path.splitext(file)[1].lower()]
            with open(file, "rb") as f:
                data = f.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError("too big")
        except (ValueError, KeyError, OSError):
            return request.send_error(404)
        request.send_response(200)
        request.send_header("Content-Type", mime)
        request.send_header("Content-Length", str(len(data)))
        request.send_header("Cache-Control", "private, max-age=31536000, immutable")
        request.send_header("X-Content-Type-Options", "nosniff")
        request.end_headers()
        request.wfile.write(data)

    def close(self):
        self._httpd.shutdown()
        self._httpd.server_close()
