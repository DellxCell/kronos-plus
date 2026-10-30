<p align="center"><img src="ui/logo.svg" width="96" alt="Kronos Plus logo"></p>

# Kronos Plus

A companion app for **Kronos**, the offline BO7 Zombies mod. Manage, fix and make mods from one window.

It only works with files on your PC: it never touches the game while it runs and keeps your Steam install clean. It only goes online to install mods and assets from Discord, and to ask GitHub if there's a new version. It never asks for your Discord login: it reads the post you open in your own Discord app.

## Download

Get the latest zip from **[Releases](../../releases)**, unzip the whole `Kronos Plus` folder, and run `Kronos Plus.exe`.

From 1.2 on, the app updates itself: when a new release is out it shows **Update now**.

Every release zip is built by GitHub Actions straight from this code (see the Actions tab), so what you download is what you can read here.

Windows may say "Windows protected your PC" because the app isn't code-signed. Click **More info → Run anyway**.

## Features

**For players**
- Mod manager: turn mods on/off, save presets, undo any change
- Install from Discord: paste a #mods or #assets post link (or a file link) and it finds the files for you (safety-checked first)
- Assets: browse Kronos's images, Lua and other assets with previews, add new ones, delete what you don't want
- Packs: every install is one pack you can turn off, uninstall (your original files come back) or update from its Discord post
- Profiles: save your whole setup, mods and packs, and switch in one click
- Add mods & packs: drop in .gsc files, assets or a whole .zip pack
- Check before you play: every mod is compiled and checked before the game opens
- Safe mode: all mods off in one click, back on when you're done
- Find the crashing mod: a guided search that narrows it down for you
- Crash suspects & play history: see which mods were on when the game crashed
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

`vendor/comtypes` is a copy of [comtypes](https://github.com/enthought/comtypes) 1.4.17 (MIT, see `vendor/comtypes-LICENSE.txt`) with its Windows UI Automation bindings already generated, used to read the Discord post you have open.
