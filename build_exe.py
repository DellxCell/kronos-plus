"""Build the Kronos Plus release: dist/Kronos Plus/ (exe + _internal) and dist/Kronos Plus <version>.zip.

Run: python build_exe.py
python build_exe.py --console builds a copy that shows errors in a console window instead.

It's a folder build on purpose: a one-file exe unpacks itself into a temp folder
every run, which antivirus programs often mistake for malware.
"""

import hashlib
import os
import shutil
import sys
import tempfile

import PyInstaller.__main__

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = (1, 0, 2, 0)
NAME = "Kronos Plus"
CONSOLE = "--console" in sys.argv
DIST = os.path.join(HERE, "dist-console" if CONSOLE else "dist")
VER = ".".join(map(str, VERSION[:3]))

version_info = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={VERSION}, prodvers={VERSION}),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('FileDescription', '{NAME}'),
    StringStruct('ProductName', '{NAME}'),
    StringStruct('FileVersion', '{VER}'),
    StringStruct('ProductVersion', '{VER}'),
    StringStruct('OriginalFilename', '{NAME}.exe'),
    StringStruct('LegalCopyright', 'Companion app for the Kronos BO7 Zombies mod')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)"""

work = tempfile.mkdtemp(prefix="kp-build-")
try:
    with open(os.path.join(work, "version.txt"), "w", encoding="utf-8") as f:
        f.write(version_info)
    PyInstaller.__main__.run([
        os.path.join(HERE, "app.py"),
        "--name", NAME,
        "--onedir",
        "--console" if CONSOLE else "--windowed",
        "--noupx",  # packed exes look suspicious to antivirus
        "--icon", os.path.join(HERE, "kronos_plus.ico"),
        "--version-file", os.path.join(work, "version.txt"),
        "--add-data", f"{os.path.join(HERE, 'ui')};ui",
        "--add-data", f"{os.path.join(HERE, 'kronos_plus.ico')};.",
        "--distpath", DIST,
        "--workpath", os.path.join(work, "build"),
        "--specpath", work,
        "--noconfirm",
        "--clean",
    ])
finally:
    shutil.rmtree(work, ignore_errors=True)

if not CONSOLE:
    app_dir = os.path.join(DIST, NAME)
    with open(os.path.join(app_dir, f"{NAME}.exe"), "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest().upper()
    with open(os.path.join(HERE, "README_release.txt"), encoding="utf-8") as f:
        readme = f.read().format(version=VER, sha256=sha)
    with open(os.path.join(app_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme)
    for old in os.listdir(DIST):
        if old.endswith(".zip"):
            os.remove(os.path.join(DIST, old))
    zip_path = shutil.make_archive(os.path.join(DIST, f"{NAME} {VER}"), "zip", DIST, NAME)
    print(f"\nRelease: {zip_path}\nSHA256 of {NAME}.exe: {sha}")
