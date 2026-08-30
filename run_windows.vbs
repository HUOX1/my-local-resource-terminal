Option Explicit
Dim shell, fso, baseDir, pythonw, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
baseDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = fso.BuildPath(baseDir, ".venv\Scripts\pythonw.exe")

If Not fso.FileExists(pythonw) Then
    MsgBox "Virtual environment not found. Run setup_windows.bat first.", 48, "G3"
    WScript.Quit 1
End If

shell.CurrentDirectory = baseDir
command = Chr(34) & pythonw & Chr(34) & " -m g3_launcher"
shell.Run command, 0, False
