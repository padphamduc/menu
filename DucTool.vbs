Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\duc"

' Chạy ngầm launcher_online.py bằng pythonw: Không hiện cửa sổ đen, mở NGAY LẬP TỨC trong 0.2s!
' Nếu máy chưa cài Python, tự động chạy DucTool.exe!
On Error Resume Next
WshShell.Run "pythonw.exe ""C:\duc\launcher_online.py""", 0, False
If Err.Number <> 0 Then
    Err.Clear
    WshShell.Run """C:\duc\DucTool.exe""", 1, False
End If
