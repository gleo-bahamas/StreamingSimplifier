#Persistent
SetTitleMatchMode, 2

; F2: launch the NBA + MLB cycler, or bring it forward if already running.
F2::
    appWindowTitle := "NBA + MLB Cycler"
    If WinExist(appWindowTitle)
    {
        WinActivate, %appWindowTitle%
        return
    }
    Run, "%A_ScriptDir%\launch.bat",, Hide
return
