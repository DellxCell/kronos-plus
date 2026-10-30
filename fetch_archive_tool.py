"""Fetch the pinned official 7-Zip distribution at build time, never at app startup."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import urllib.request

VERSION = "26.05"
URL = "https://github.com/ip7z/7zip/releases/download/26.05/7z2605-x64.exe"
PACKAGE_SHA256 = "FD99E86F57D8F429EF5ED045BF98315AF962E2309B0F1BA87A147A44C71647D0"
BINARIES = {
    "7z.exe": "94205CFC054DD3BBEB978905BC619A65B3F04E9E73BB2717841110B6F46D962E",
    "7z.dll": "78BF6B668D75801E3AA180B4CCB16E6D8395FBA80DEC8A065055BB6F8DFABB82",
}


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def ensure_archive_tool():
    destination = Path(__file__).resolve().parent / "vendor" / "7zip"
    if all((destination / name).is_file() and checksum(destination / name) == digest
           for name, digest in BINARIES.items()) and (destination / "License.txt").is_file():
        return destination
    tar = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tar.exe"
    with tempfile.TemporaryDirectory(prefix="kp-7zip-build-") as temporary:
        staging = Path(temporary)
        installer = staging / "official-7zip.exe"
        with urllib.request.urlopen(URL, timeout=30) as source:
            data = source.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024 or hashlib.sha256(data).hexdigest().upper() != PACKAGE_SHA256:
            raise RuntimeError("The official 7-Zip package didn't match its pinned checksum")
        installer.write_bytes(data)
        # Read only these three known members; the installer is never executed.
        subprocess.run([str(tar), "-xf", str(installer), "-C", str(staging),
                        "7z.exe", "7z.dll", "License.txt"], check=True, timeout=30,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for name, digest in BINARIES.items():
            if checksum(staging / name) != digest:
                raise RuntimeError("7-Zip's extracted binaries didn't match their pinned checksums")
        destination.mkdir(parents=True, exist_ok=True)
        for name in [*BINARIES, "License.txt"]:
            shutil.copyfile(staging / name, destination / name)
    return destination


if __name__ == "__main__":
    print(ensure_archive_tool())
