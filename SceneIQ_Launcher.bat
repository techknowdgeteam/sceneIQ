@echo off
setlocal
set "SCENEIQ_DIR=%~dp0"
set "SCENEIQ_VBS=%SCENEIQ_DIR%Start_SceneIQ.vbs"
if not exist "%SCENEIQ_VBS%" (
  echo SceneIQ launcher is missing: "%SCENEIQ_VBS%"
  echo Extract the complete SceneIQ package and try again.
  pause
  exit /b 2
)
start "" "%SystemRoot%\System32\wscript.exe" "%SCENEIQ_VBS%"
exit /b 0
