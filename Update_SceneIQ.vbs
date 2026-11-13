Option Explicit
Dim fso, shell, baseDir, targetFile, pythonw, localAppData, pathValue, entries, item
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
baseDir = fso.GetParentFolderName(WScript.ScriptFullName)
targetFile = fso.BuildPath(baseDir, "sceniq_updater.pyw")
If Not fso.FileExists(targetFile) Then
    MsgBox "Update SceneIQ component is missing: sceniq_updater.pyw. Re-extract or reinstall the complete SceneIQ package.", vbCritical, "Update SceneIQ"
    WScript.Quit 2
End If

pythonw = ""
localAppData = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
If fso.FileExists("C:\Program Files\Python310\pythonw.exe") Then pythonw = "C:\Program Files\Python310\pythonw.exe"
If pythonw = "" And localAppData <> "%LOCALAPPDATA%" Then
    If fso.FileExists(localAppData & "\Programs\Python\Python310\pythonw.exe") Then pythonw = localAppData & "\Programs\Python\Python310\pythonw.exe"
End If
If pythonw = "" And fso.FileExists("C:\Program Files\Python311\pythonw.exe") Then pythonw = "C:\Program Files\Python311\pythonw.exe"
If pythonw = "" And fso.FileExists("C:\Program Files\Python312\pythonw.exe") Then pythonw = "C:\Program Files\Python312\pythonw.exe"
If pythonw = "" And localAppData <> "%LOCALAPPDATA%" Then
    If fso.FileExists(localAppData & "\Programs\Python\Python311\pythonw.exe") Then pythonw = localAppData & "\Programs\Python\Python311\pythonw.exe"
    If pythonw = "" And fso.FileExists(localAppData & "\Programs\Python\Python312\pythonw.exe") Then pythonw = localAppData & "\Programs\Python\Python312\pythonw.exe"
End If
If pythonw = "" Then
    pathValue = shell.ExpandEnvironmentStrings("%PATH%")
    entries = Split(pathValue, ";")
    For Each item In entries
        item = Replace(item, Chr(34), "")
        If Len(Trim(item)) > 0 Then
            If fso.FileExists(fso.BuildPath(Trim(item), "pythonw.exe")) Then pythonw = fso.BuildPath(Trim(item), "pythonw.exe"): Exit For
        End If
    Next
End If
If pythonw = "" Then
    MsgBox "Python 3.10, 3.11 or 3.12 with Tcl/Tk could not be found. Install Python for Windows with Tcl/Tk, then run Install_SceneIQ.vbs again.", vbExclamation, "SCiQ Setup"
    WScript.Quit 3
End If
shell.CurrentDirectory = baseDir
shell.Run Chr(34) & pythonw & Chr(34) & " " & Chr(34) & targetFile & Chr(34), 0, False
