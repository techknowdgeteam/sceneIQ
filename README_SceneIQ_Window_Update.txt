SCiQ / SceneIQ — HOME VIEW AND WINDOW UPDATE

WHAT CHANGED
1. SceneIQ opens to a Home view in both the Video Producer and Image Producer tabs.
2. The Home view randomly selects an animated GIF from:
   C:\xampp\htdocs\AI automation\ai cover
   If no GIF is found or it cannot be read, the built-in SCiQ robot artwork is shown.
3. Video production does not start automatically. In the Video Producer command deck:
   - CONFIGURATION opens its editor inside the current SceneIQ window.
   - PRODUCTION opens the video-production grid only; it does not start workers.
   - START PRODUCTION (directly below PRODUCTION) starts the video service and queue.
4. Video issues/reports, video console, configuration, image console and image
   configuration are displayed inside the existing SceneIQ window. Each view has
   a BACK TO HOME control at the upper-right edge.
5. Closing SceneIQ no longer displays an exit-confirmation window. If a producer
   is active, SceneIQ sends its normal stop request and closes the desktop window.
6. Vertical and horizontal scrollbars use the dark SCiQ palette, not white troughs.
7. The WAITING FOR VIDEO WORK area is more compact so the project cards have more
   room in the production view.

INSTALL / UPDATE
1. Extract every file in this ZIP into one folder in Downloads.
2. Run Install_SceneIQ.vbs for a fresh installation, or run Update_SceneIQ.vbs
   from the installed SceneIQ folder and select the latest update.
3. The setup process copies the complete latest extracted package into:
   C:\xampp\htdocs\AI automation\scenIQ
   Matching files are overwritten; destination-only files are preserved.
4. Start SceneIQ using Start_SceneIQ.vbs or the SceneIQ desktop shortcut.

SCOPE
The Video Producer desktop/window code was updated to provide the requested UI
and navigation. The image-production engine is included unchanged. No production
engine workflow, rendering, generation or queue logic was intentionally modified.

COMMAND DECK AND SCROLLBAR FIX
1. The Video Producer COMMAND DECK now has its own vertical scrollbar. Scroll it with the rail or mouse wheel while the pointer is over the command deck.
2. Vertical and horizontal scrollbars throughout the SceneIQ window use the SCiQ dark palette: dark trough/background, dark track, and cyan active accents.
3. This update is limited to desktop-window scrolling and scrollbar styling. Video and image production engines are not otherwise changed.
