' Double-click: starts the ITE quiz and opens your browser (public trycloudflare link).
' No black Command Prompt window. Keep this PC on while presenting.
'
' To stop: Task Manager -> end "Python" and "cloudflared"
' If nothing opens, see: run_live_errors.txt (created in this folder)

Option Explicit

Dim fso, folder, sh, cmdline

Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = folder

' Hidden window (0). Do not wait for process (False).
cmdline = "cmd /c cd /d " & Chr(34) & folder & Chr(34) & " && " & _
          "(py -3 run_live.py 1>run_live_errors.txt 2>&1) || " & _
          "(python run_live.py 1>run_live_errors.txt 2>&1)"

sh.Run cmdline, 0, False
