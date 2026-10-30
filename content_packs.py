"""Plan and install Kronos source mods and assets without extracting arbitrary paths."""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import stat
import tempfile
import uuid
import zipfile

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".dds", ".tga", ".bmp", ".webp"}
ASSET_RULES = {
    "Lua": {".lua"},
    "Images": IMAGE_EXTENSIONS | {".txt"},
    "Camos": {".json", ".csv", ".txt"},
    "MapEnts": {".mapents", ".ents", ".txt", ".csv"},
    "Rawfiles": {".raw", ".bin", ".txt", ".json", ".cfg", ".ini", ".xml", ".csv", ".tsv"},
    "Scripts": {".gsc", ".csc"},
    "StringTable": {".csv", ".tsv", ".txt"},
}
ASSET_EXTENSIONS = set().union(*ASSET_RULES.values()) - {".gsc"}
DEFAULT_FOLDERS = {".lua": "Lua", **{ext: "Images" for ext in IMAGE_EXTENSIONS},
                   ".csv": "StringTable", ".tsv": "StringTable", ".csc": "Scripts",
                   ".mapents": "MapEnts", ".ents": "MapEnts", ".raw": "Rawfiles", ".bin": "Rawfiles",
                   ".cfg": "Rawfiles", ".ini": "Rawfiles", ".xml": "Rawfiles"}
MAX_ASSET_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_FILES = 5000
MAX_SOURCE_BYTES = 1024 * 1024
FOLDERS_BY_CASE = {name.casefold(): name for name in ASSET_RULES}
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def safe_parts(name):
    if not isinstance(name, str) or not name or name.startswith(("/", "\\")):
        raise ValueError("Absolute or empty file path")
    parts = name.replace("\\", "/").split("/")
    if any(not p or p in {".", ".."} or p.endswith((".", " ")) or RESERVED.match(p)
           or re.search(r'[<>:"|?*\x00-\x1f]', p) for p in parts):
        raise ValueError("Unsafe file path")
    return parts


def asset_folders_for(name):
    ext = os.path.splitext(name)[1].lower()
    return [folder for folder, extensions in ASSET_RULES.items() if ext in extensions]


def image_bucket(name):
    base = name.lower()
    if base.startswith("ui_icon_perks_"):
        return "perks"
    if base.startswith(("sat_ui_hud_zm_powerup_icon_", "ui_icon_powerup_")):
        return "powerups"
    return None


def asset_target(name, folder=None):
    parts = safe_parts(name)
    if len(parts) != 1:
        raise ValueError("Use a file name for a standalone asset")
    folder = FOLDERS_BY_CASE.get((folder or DEFAULT_FOLDERS.get(os.path.splitext(name)[1].lower(), "")).casefold())
    if not folder or folder not in asset_folders_for(name):
        raise ValueError("Choose the asset's destination folder")
    bucket = image_bucket(name) if folder == "Images" else None
    return f"Assets/Images/{bucket}/Imported icons/{name}" if bucket else f"Assets/{folder}/{name}"


def classify_archive_path(name, manifest_suffix, pack_label="Imported icons"):
    parts = safe_parts(name)
    folded = [part.casefold() for part in parts]
    if "assets" in folded:
        index = folded.index("assets")
        if len(parts) < index + 3 or folded[index + 1] not in FOLDERS_BY_CASE:
            raise ValueError("Unknown asset folder")
        folder = FOLDERS_BY_CASE[folded[index + 1]]
        return "/".join(["Assets", folder, *parts[index + 2:]])
    # Some authors zip Lua/ or Images/ directly, without an Assets/ wrapper.
    for index, part in enumerate(folded[:-1]):
        if part in FOLDERS_BY_CASE and part != "scripts":
            return "/".join(["Assets", FOLDERS_BY_CASE[part], *parts[index + 1:]])
    base = parts[-1]
    if base.lower().endswith((".gsc", manifest_suffix)):
        return base
    extension = os.path.splitext(base)[1].lower()
    if extension in IMAGE_EXTENSIONS:
        bucket_index = next((i for i, part in enumerate(folded[:-1]) if part in {"perks", "powerups"}), None)
        bucket = folded[bucket_index] if bucket_index is not None else image_bucket(base)
        if bucket:
            if bucket_index is not None and len(parts) > bucket_index + 2:
                return "/".join(["Assets", "Images", bucket, *parts[bucket_index + 1:]])
            parents = parts[:bucket_index] if bucket_index is not None else parts[:-1]
            label = parents[-1] if parents else pack_label
            if len(safe_parts(label)) != 1:
                raise ValueError("Invalid icon pack name")
            return f"Assets/Images/{bucket}/{label}/{base}"
    # Shared assets are often wrapped in an author-named folder rather than Assets/.
    if extension in DEFAULT_FOLDERS:
        return asset_target(base)
    raise ValueError("No supported mod or asset destination")


def validate_asset(relative, data):
    parts = safe_parts(relative)
    if len(parts) < 3 or parts[0] != "Assets" or parts[1] not in ASSET_RULES:
        raise ValueError("Unknown asset destination")
    ext = os.path.splitext(parts[-1])[1].lower()
    if ext not in ASSET_RULES[parts[1]]:
        raise ValueError(f"Unsupported file type for Assets/{parts[1]}")
    if len(data) > MAX_ASSET_BYTES:
        raise ValueError("Asset exceeds the 32 MB file limit")
    if data.startswith((b"MZ", b"\x7fELF")):
        raise ValueError("Executable data is not an asset")
    if ext in IMAGE_EXTENSIONS:
        valid = {
            ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
            ".jpg": data.startswith(b"\xff\xd8\xff"), ".jpeg": data.startswith(b"\xff\xd8\xff"),
            ".dds": data.startswith(b"DDS "), ".bmp": data.startswith(b"BM"),
            ".webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
            ".tga": len(data) >= 18 and data[2] in {1, 2, 3, 9, 10, 11},
        }[ext]
        if not valid:
            raise ValueError("File data does not match its image extension")
    elif ext not in {".bin", ".raw"}:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("Asset is not readable UTF-8 text") from None
        if "\x00" in text:
            raise ValueError("Text asset contains binary data")
        if ext == ".json":
            try:
                json.loads(text)
            except ValueError:
                raise ValueError("Asset is not valid JSON") from None


def read_content_pack(path, check_source, manifest_suffix, clean_manifest, pack_info, asset_folder=None):
    name = os.path.splitext(os.path.basename(path))[0]
    archive_label = name
    if not path.lower().endswith(".zip"):
        target = asset_target(os.path.basename(path), asset_folder)
        with open(path, "rb") as file:
            data = file.read(MAX_ASSET_BYTES + 1)
        validate_asset(target, data)
        return name, {target: data}, []
    good, bad, seen, total = {}, [], set(), 0
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ARCHIVE_FILES:
            raise ValueError("Archive has too many files")
        for info in entries:
            if info.is_dir():
                continue
            try:
                parts = safe_parts(info.filename)
                if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
                    raise ValueError("Archive links are not installed")
                if info.flag_bits & 1:
                    raise ValueError("Encrypted files are not supported")
                total += info.file_size
                if total > MAX_EXPANDED_BYTES:
                    raise ValueError("Archive exceeds the 128 MB expanded-size limit")
                if info.file_size > MAX_ASSET_BYTES:
                    raise ValueError("File exceeds the 32 MB limit")
                if parts[-1] == pack_info:
                    if info.file_size > MAX_SOURCE_BYTES:
                        raise ValueError("Pack manifest is too large")
                    try:
                        metadata = json.loads(archive.read(info))
                        if isinstance(metadata, dict) and isinstance(metadata.get("name"), str):
                            name = metadata["name"][:200] or name
                    except ValueError:
                        pass
                    continue
                relative = classify_archive_path(info.filename, manifest_suffix, archive_label)
                if relative.casefold() in seen:
                    raise ValueError("Duplicate destination in this archive")
                seen.add(relative.casefold())
                limit = MAX_ASSET_BYTES if relative.startswith("Assets/") else MAX_SOURCE_BYTES
                if info.file_size > limit:
                    raise ValueError("File exceeds the size limit for its type")
                data = archive.read(info)
                if relative.startswith("Assets/"):
                    validate_asset(relative, data)
                elif relative.lower().endswith(manifest_suffix):
                    manifest = json.loads(data.decode("utf-8-sig"))
                    if not isinstance(manifest, dict):
                        raise ValueError("Invalid mod manifest")
                    data = json.dumps(clean_manifest(manifest), indent=4).encode("utf-8")
                else:
                    problem = check_source(relative, data)
                    if problem:
                        raise ValueError(problem)
                good[relative] = data
            except (ValueError, UnicodeDecodeError, RuntimeError, NotImplementedError) as error:
                if total > MAX_EXPANDED_BYTES:
                    raise ValueError("Archive exceeds the 128 MB expanded-size limit") from error
                bad.append(f"{info.filename}: {error}")
    return name, good, bad


def destination_for(relative, scripts_root, assets_root, manifest_suffix):
    parts = safe_parts(relative)
    if parts[0] == "Assets":
        if len(parts) < 3 or parts[1] not in ASSET_RULES:
            raise ValueError("Unknown asset destination")
        if os.path.splitext(parts[-1])[1].lower() not in ASSET_RULES[parts[1]]:
            raise ValueError("Unsupported asset file type")
        root, leaf = assets_root, parts[1:]
    elif len(parts) == 1 and relative.lower().endswith((".gsc", manifest_suffix)):
        root, leaf = scripts_root, parts
    else:
        raise ValueError("Unsupported installation destination")
    root = os.path.abspath(root)
    destination = os.path.join(root, *leaf)
    resolved_root, resolved_destination = os.path.realpath(root), os.path.realpath(destination)
    if os.path.commonpath([resolved_root, resolved_destination]) != resolved_root or resolved_destination == resolved_root:
        raise ValueError("Destination leaves the selected folder")
    # Do not install through a symbolic link or directory junction.
    current = root
    for part in leaf:
        current = os.path.join(current, part)
        if os.path.lexists(current):
            attributes = os.lstat(current)
            if stat.S_ISLNK(attributes.st_mode) or getattr(attributes, "st_file_attributes", 0) & 0x400:
                raise ValueError("Destination contains a link or junction")
    return destination


def install_content_files(files, overwrite_names, destination, backup_root):
    """Install a reviewed plan; retain originals and roll back this batch if a write fails."""
    overwrite = {name.casefold() for name in overwrite_names}
    pending, skipped = [], []
    for relative, data in files.items():
        path = destination(relative)
        if os.path.exists(path) and relative.casefold() not in overwrite:
            skipped.append(relative)
        else:
            pending.append((relative, data, path))
    batch = os.path.join(backup_root, "content", datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex)
    written, originals, staged = [], {}, []
    try:
        for relative, data, path in pending:
            # Revalidate before every write, including after parent creation.
            destination(relative)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            destination(relative)
            if os.path.exists(path):
                saved_parts = safe_parts(relative if relative.startswith("Assets/") else "custom_scripts/" + relative)
                saved = os.path.join(batch, *saved_parts)
                os.makedirs(os.path.dirname(saved), exist_ok=True)
                shutil.copy2(path, saved)
                originals[relative] = saved
            handle, temporary = tempfile.mkstemp(prefix=".kp-install-", dir=os.path.dirname(path))
            staged.append(temporary)
            with os.fdopen(handle, "wb") as output:
                output.write(data)
            destination(relative)
            os.replace(temporary, path)
            written.append((relative, path))
    except Exception:
        for relative, path in reversed(written):
            destination(relative)
            if relative in originals:
                shutil.copy2(originals[relative], path)
            else:
                os.remove(path)
        raise
    finally:
        for temporary in staged:
            if os.path.isfile(temporary):
                os.remove(temporary)
    return {"installed": [relative for relative, _ in written], "skipped": skipped,
            "backup": batch if originals else None}
