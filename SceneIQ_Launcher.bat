@echo off
setlocal

REM SceneIQ shared-window launcher.
REM This launches ONLY the shared desktop application.
REM The Image Producer is started from its tab inside that window.

set "SCENEIQ_DIR=C:\xampp\htdocs\AI automation\scenIQ"
set "MAIN_SCRIPT=%SCENEIQ_DIR%\sceneiqvideoproduction.py"
set "PYTHONW_EXE=C:\Program Files\Python310\pythonw.exe"

if not exist "%MAIN_SCRIPT%" (
    echo [ERROR] SceneIQ shared-window script was not found:
    echo "%MAIN_SCRIPT%"
    echo.
    echo Make sure sceneiqvideoproduction.py is in the SceneIQ folder.
    pause
    exit /b 1
)

if not exist "%PYTHONW_EXE%" (
    echo [ERROR] Python 3.10 windowed executable was not found:
    echo "%PYTHONW_EXE%"
    echo.
    echo Check your Python installation or update PYTHONW_EXE in this BAT file.
    pause
    exit /b 1
)

REM START uses an empty window title ("") followed by the quoted executable.
REM pythonw.exe launches Tkinter without keeping a Command Prompt window open.
start "" /D "%SCENEIQ_DIR%" "%PYTHONW_EXE%" "%MAIN_SCRIPT%"

endlocal
exit /b 0
