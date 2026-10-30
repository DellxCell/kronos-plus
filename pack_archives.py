"""Read pack archives as bounded byte streams, never extract their paths to disk."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

ARCHIVE_EXTENSIONS = {".zip", ".7z", ".rar"}


def tool_path():
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / "vendor" / "7zip" / "7z.exe"


def _run(arguments, limit, timeout=30):
    tool = tool_path()
    if not tool.is_file() or not tool.with_name("7z.dll").is_file():
        raise ValueError("Archive support is missing. Unzip the whole Kronos Plus download and try again.")
    # No shell, no PATH lookup, no output directory, no archive-supplied command options.
    with tempfile.TemporaryFile() as output:
        child = subprocess.Popen([str(tool), *arguments], stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.DEVNULL, cwd=str(tool.parent),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        deadline = time.monotonic() + timeout
        try:
            while child.poll() is None:
                if os.fstat(output.fileno()).st_size > limit:
                    raise ValueError("Archive data exceeds its size limit")
                if time.monotonic() >= deadline:
                    raise ValueError("The archive took too long to read. Try a smaller pack.")
                time.sleep(0.02)
            if os.fstat(output.fileno()).st_size > limit:
                raise ValueError("Archive data exceeds its size limit")
            if child.returncode != 0:
                raise ValueError("Couldn't read this archive. Password-protected, damaged and multipart archives aren't supported.")
            output.seek(0)
            return output.read(limit + 1)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()


@dataclass(frozen=True)
class Entry:
    filename: str
    file_size: int
    directory: bool = False
    external_attr: int = 0
    flag_bits: int = 0

    def is_dir(self):
        return self.directory


def parse_listing(data, max_files, max_expanded):
    try:
        text = data.decode("utf-8-sig", errors="strict").replace("\r\n", "\n")
    except UnicodeDecodeError:
        raise ValueError("The archive has unreadable file names") from None
    if re.search(r"[\x00-\x09\x0b-\x1f]", text):
        raise ValueError("The archive has unsupported control characters")
    entries, seen, total = [], set(), 0
    for block in re.split(r"\n{2,}", text.strip("\n")):
        if not block.strip():
            continue
        fields = {}
        for line in block.splitlines():
            key, separator, val = line.partition(" = ")
            if not separator or not key or key in fields:
                raise ValueError("The archive has ambiguous file metadata")
            fields[key] = val
        name = fields.get("Path", "")
        size = fields.get("Size", "")
        if not name or not re.fullmatch(r"[0-9]{1,16}", size):
            raise ValueError("The archive has invalid file metadata")
        if name.casefold() in seen:
            raise ValueError("The archive contains duplicate file names")
        seen.add(name.casefold())
        attributes = fields.get("Attributes", "")
        mode = fields.get("Mode", "")
        link = (any(fields.get(key) not in (None, "", "-") for key in
                    ("Symbolic Link", "Hard Link", "Copy Link", "Reparse Point"))
                or bool(re.search(r"(?:^|\s)l[rwxstST-]{9}(?:\s|$)", attributes + " " + mode)))
        if any(fields.get(key) == "+" for key in ("Alternate Stream", "Split Before", "Split After")):
            raise ValueError("Archive streams and multipart files aren't supported")
        directory = fields.get("Folder") == "+" or attributes.startswith("D")
        length = int(size)
        total += length
        if total > max_expanded:
            raise ValueError("Archive exceeds the 128 MB expanded-size limit")
        entries.append(Entry(name, length, directory, stat.S_IFLNK << 16 if link else 0,
                             1 if fields.get("Encrypted") == "+" else 0))
        if len(entries) > max_files:
            raise ValueError("Archive has too many files")
    return entries


class SevenZipArchive:
    def __init__(self, path, max_files, max_expanded):
        self.path = os.path.abspath(path)
        with open(self.path, "rb") as source:
            signature = source.read(8)
        if self.path.lower().endswith(".7z") and signature.startswith(b"7z\xbc\xaf\x27\x1c"):
            self.format = "-t7z"
        elif self.path.lower().endswith(".rar") and signature.startswith(b"Rar!\x1a\x07\x01\x00"):
            self.format = "-tRar5"
        elif self.path.lower().endswith(".rar") and signature.startswith(b"Rar!\x1a\x07\x00"):
            self.format = "-tRar"
        else:
            raise ValueError("Couldn't read this archive. Its contents don't match the file type.")
        self.deadline = time.monotonic() + 60
        listing = _run(["l", self.format, "-slt", "-ba", "-bd", "-sccUTF-8", "-p", "--", self.path], 8 * 1024 * 1024)
        self.entries = parse_listing(listing, max_files, max_expanded)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def infolist(self):
        return list(self.entries)

    def read(self, entry):
        if entry not in self.entries or entry.is_dir() or entry.external_attr or entry.flag_bits:
            raise ValueError("Archive links and encrypted files are not installed")
        timeout = self.deadline - time.monotonic()
        if timeout <= 0:
            raise ValueError("The archive took too long to read. Try a smaller pack.")
        data = _run(["x", self.format, "-so", "-bd", "-bb0", "-p", "-spd", "-ssc", "--", self.path, entry.filename],
                    entry.file_size, min(30, timeout))
        if len(data) != entry.file_size:
            raise ValueError("Archive file size changed while reading")
        return data


def open_archive(path, max_files=5000, max_expanded=128 * 1024 * 1024):
    if os.path.splitext(path)[1].lower() == ".zip":
        return zipfile.ZipFile(path)
    return SevenZipArchive(path, max_files, max_expanded)
