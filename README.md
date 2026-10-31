<p align="center"><img src="ui/logo.svg" width="96" alt="Kronos Plus logo"></p>

# Kronos Plus

A companion app for **Kronos**, the offline BO7 Zombies mod. Manage, fix and make mods from one window.

It only works with files on your PC: it never touches the game while it runs and keeps your Steam install clean. It only goes online to install mods and assets from Discord, and to ask GitHub if there's a new version. It never asks for your Discord login: it reads the post you open in your own Discord app, and for code previews it clicks that preview's Download button there for you.

## Download

Get the latest zip from **[Releases](../../releases)**, unzip the whole `Kronos Plus` folder, and run `Kronos Plus.exe`.

From 1.2 on, the app updates itself: when a new release is out it shows **Update now**, and after updating it shows what's new.

Every release zip is built by GitHub Actions straight from this code (see the Actions tab), so what you download is what you can read here.

Windows may say "Windows protected your PC" because the app isn't code-signed. Click **More info → Run anyway**.

## Features

**For players**
- Mod manager: turn mods on/off (precompiled .gscc ones too), save presets, undo any change
- Refresh: the button next to Play (or F5) picks up changes made outside the app
- Rename mods: right-click a mod (or press F2) to show it under a name you pick; the file stays the same
- Install from Discord: paste a #mods or #assets post link (or a file link), pick the attachments you want and it downloads them, code previews included (safety-checked first)
- Assets: browse Kronos's images, Lua and other assets with previews, add new ones, delete what you don't want
- Packs: every install is one pack you can turn off, uninstall (your original files come back) or update from its Discord post
- Profiles: save your whole setup, mods and packs, and switch in one click
- Add mods & packs: drop in or Ctrl+V .gsc or precompiled .gscc files, assets or a whole .zip, .7z or .rar pack; it works out what's a mod and what's an asset
- Play in one click: every mod is compiled and checked, then the game starts through Kronos's launcher
- Safe mode: all mods off in one click, back on when you're done
- Find the crashing mod: a guided search that narrows it down for you
- Crash suspects & play history: see which mods were on when the game crashed
- Ask for help: copy a report of your mods, health check and latest errors to paste in the Kronos Discord (your Windows user folder and in-game name are left out)
- Full backup: save mods, assets, packs, presets and settings in one file, and restore it in one click
- Settings editor: Kronos's gameplay options, name and keys, with backups
- Health check: Kronos set up right, Steam folder clean, BO7 update warnings, mod conflicts

**For modders** (turn on Developer mode in Settings)
- Studio: new mod from a template in seconds
- Code editor: GSC highlighting, autocomplete, auto-indent, auto backups
- Live problem checking: catches loops with no wait, missing #using and more as you type
- Compile check: uses Kronos's own compiler, errors jump to the line
- Test alone: play with only your mod, then your setup comes back by itself
- Manifests: version, author and requirements, missing ones flagged
- Live console: launcher log, crashes and match results as they happen

## Requirements

- Windows 10 or 11 with Microsoft Edge WebView2 (built into Windows 11)
- Kronos set up (run the Kronos launcher at least once)

## Run from source

```
pip install -r requirements.txt
python app.py
```

Build the release zip yourself with `python build_exe.py` (output in `dist/`).

`vendor/comtypes` is a copy of [comtypes](https://github.com/enthought/comtypes) 1.4.17 (MIT, see `vendor/comtypes-LICENSE.txt`) with its Windows UI Automation bindings already generated, used to read the Discord post you have open and click a code preview's Download button.

At build time `fetch_archive_tool.py` downloads the official [7-Zip](https://www.7-zip.org) 26.05 (LGPL, see its `License.txt`), checks it against pinned SHA-256 hashes and bundles `7z.exe`/`7z.dll` to read .7z and .rar packs.
