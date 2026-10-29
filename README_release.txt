Kronos Plus {version}
=================

A companion app for Kronos, the offline BO7 Zombies mod. Manage, fix and make
mods from one window. It only works with files on your PC: it never touches the
game while it runs, never goes online, and keeps your Steam install clean.

What you need
-------------
- Windows 10 or 11
- Kronos already set up (run the Kronos launcher at least once)
- Microsoft Edge WebView2 (built into Windows 11; most Windows 10 PCs have it too)

How to run it
-------------
1. Unzip the whole "Kronos Plus" folder anywhere you like, for example Documents.
   Keep the _internal folder next to the .exe: the app needs it.
2. Double-click "Kronos Plus.exe". Nothing to install.
   Tip: right-click the .exe > Send to > Desktop (create shortcut).

Windows may show "Windows protected your PC" the first time, because the app
isn't signed with a paid certificate. Click "More info", then "Run anyway".

Kronos Plus finds Kronos by itself. If it can't find KronosLauncher.exe when you
press Play, it asks you to pick it once and remembers it.

Where your stuff is saved
-------------------------
Presets, play history and settings backups:  %LOCALAPPDATA%\Kronos Plus
Your mods stay in Kronos's own custom_scripts folder.

To remove Kronos Plus, delete the "Kronos Plus" folder and that folder.

Check your download
-------------------
SHA256 of Kronos Plus.exe:
{sha256}

In PowerShell:  Get-FileHash "Kronos Plus.exe"
If the hash doesn't match, don't run it.
