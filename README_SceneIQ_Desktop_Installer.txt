SCiQ / SCENEIQ DESKTOP INSTALLER & ONE-CLICK UPDATER
===================================================

WHAT THIS PACKAGE INSTALLS
--------------------------
- One SCiQ desktop application with the Video Producer and Image Producer tabs.
- The Video Producer remains the default tab when SceneIQ opens.
- The Image Producer runs as an isolated worker and keeps its own progress HUD.
- Image Producer keyboard shortcuts remain isolated to that worker:
    Ctrl + Shift + F12  restart image workflow
    Alt + /             stop image production and return focus to the SCiQ window
- A SceneIQ desktop shortcut and a separate Update SceneIQ shortcut.
- A setup/dependency checker, quiet VBS launchers, a custom SCiQ icon and installer artwork.

FIRST INSTALLATION
------------------
1. Extract the complete ZIP package to a normal folder (Downloads is fine).
2. Double-click Install_SceneIQ.vbs.
3. The SCiQ setup window creates the required SceneIQ folders, installs both producer
   scripts, checks Python imports used by both engines, installs missing packages in
   the background, validates syntax and verifies desktop shortcuts.
4. The installer creates and verifies four shortcuts:
   - Windows Desktop: SceneIQ
   - Windows Desktop: Update SceneIQ
   - Start Menu > Programs > SceneIQ: SceneIQ
   - Start Menu > Programs > SceneIQ: Update SceneIQ
5. SceneIQ opens automatically after setup succeeds.

INSTALL LOCATION
----------------
C:\xampp\htdocs\AI automation\scenIQ

DAILY LAUNCH
------------
Double-click the SceneIQ desktop shortcut or search for SceneIQ in Windows Start.
The launcher runs pythonw.exe through Windows Script Host, so no Command Prompt is
opened. Start_SceneIQ.vbs launches sceneiqvideoproduction.py directly; it does NOT
run setup, install packages, or display the installer. Install_SceneIQ.vbs is the
only first-run/setup entry point. SceneIQ is a single shared window; do not start
the image producer script separately.

UPDATING FROM DOWNLOADS
-----------------------
1. Download and extract the newest full SceneIQ update folder into Downloads.
2. Confirm that BOTH files are in that same folder:
     sceneiqvideoproduction.py
     sceniqimageproduction.py
3. Double-click Update SceneIQ on the Desktop.
4. The updater scans Downloads recursively (skipping cache/build/virtual environment
   folders), validates both producer scripts and selects the newest valid matched pair.
5. Confirm INSTALL LATEST UPDATE.
6. If SceneIQ is running, the updater asks permission to close the shared window and
   its producer workers before replacing scripts.
7. Both current scripts are backed up under _update_backups, the matched pair is
   installed, dependencies are checked, and the desktop shortcuts are refreshed.
8. The shared SCiQ desktop opens after setup succeeds.

SAFE REINSTALL / DATA PRESERVATION
----------------------------------
The installer/updater replaces only the two producer scripts and SceneIQ support files.
It does not overwrite or delete existing panel.json, ready_script.json, project images,
subscribe stickers, generated images/videos, captions, audio, checkpoints, or other
working data. Previous producer versions are retained under _update_backups.

PYTHON REQUIREMENTS
-------------------
- Windows 10/11.
- Python 3.10, 3.11 or 3.12 for Windows, installed with Tcl/Tk support (pythonw.exe).
- Internet access is needed only if a required third-party Python distribution is missing
  or needs repair.
- The installer does not install Python itself.

NOTES
-----
- The SceneIQ updater only accepts a complete matched pair of producer scripts from one
  extracted folder; it will not update just one engine by accident.
- The Image Producer's Alt+/ focus-return signal is emitted only by its keyboard shortcut.
  The Image Producer command-center Stop button does not trigger that special focus action.
- The video producer does not register or listen for the image-only keyboard shortcuts.
