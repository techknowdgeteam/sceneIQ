SCiQ / SceneIQ - Fixed Installer Package

INSTALL
1. Extract every file in this ZIP into one folder.
2. Run Install_SceneIQ.vbs.
3. The installer searches Downloads for the newest extracted folder containing
   a complete, valid pair of SceneIQ producer scripts. If none is found, it
   uses the folder containing this installer.
4. Every file and folder in the selected package is copied into:
   C:\xampp\htdocs\AI automation\scenIQ
   Files with matching names are overwritten. Destination-only files remain.
5. Setup verifies dependencies and opens the SceneIQ desktop in the same
   installer window. No installation-success OK dialog is shown.

UPDATE
1. Extract the newest SceneIQ package into Downloads.
2. Run Update_SceneIQ.vbs from the installed SceneIQ folder (or its shortcut).
3. Select INSTALL LATEST UPDATE. The newest valid extracted folder is copied
   recursively to the installation directory before setup and validation.

The application target path is fixed in the setup scripts. Keep the producer
scripts and launcher files together in the extracted package folder.
