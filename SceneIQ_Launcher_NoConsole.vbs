' Run the BAT launcher invisibly so Windows does not display its brief CMD window.
Option Explicit
Dim fso, shell, folder, batPath
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = fso.BuildPath(folder, "SceneIQ_Launcher.bat")
If Not fso.FileExists(batPath) Then
    MsgBox "SceneIQ_Launcher.bat was not found next to this VBS file.", vbCritical, "SceneIQ Launcher"
    WScript.Quit 1
End If
shell.Run Chr(34) & batPath & Chr(34), 0, False
