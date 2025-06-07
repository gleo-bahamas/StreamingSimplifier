#Persistent
; SetTitleMatchMode, 2 allows a title to contain the specified string anywhere.
; This is generally safer than 3 (starts with) or Exact (exact match).
SetTitleMatchMode, 2

F2:: ; Define action for F2 key
    ; === IMPORTANT: REPLACE THIS LINE WITH YOUR APP'S ACTUAL, EXACT WINDOW TITLE ===
    appWindowTitle := "NBA + MLB Cycler" ; e.g., "Streaming Simplifier - Main"

    ; Define the path to your launch batch file
    launchBatchFile := "C:\Users\admin\StreamingSimplifier\launch.bat"
    pythonScriptPath := "C:\Users\admin\StreamingSimplifier\main.py" ; Keep this for the optional tasklist check

    ; --- DEBUGGING MESSAGES (Uncomment to see what's happening) ---
    ; This will pop up a message box showing if the window was found or not.
    ; If WinExist(appWindowTitle)
    ; {
    ;     MsgBox, 0,, Debug: Window "%appWindowTitle%" WAS found. Activating.
    ; }
    ; else
    ; {
    ;     MsgBox, 0,, Debug: Window "%appWindowTitle%" NOT found. Attempting launch.
    ; }
    ; --- END DEBUGGING MESSAGES ---

    ; Check if the application window already exists
    If WinExist(appWindowTitle)
    {
        ; If the window exists, activate it and do nothing else (don't launch again)
        WinActivate, %appWindowTitle%
        ; MsgBox, 0,, StreamingSimplifier is already running. Activating window. ; Optional: user feedback
        return
    }
    else
    {
        ; If the window does not exist, launch the program using the batch file
        ; The 'Hide' option will hide the command prompt window that the batch file opens.
        Run, "%launchBatchFile%",, Hide

        ; Optional: Add a small delay after launch to give your Python app time to show its window.
        ; This is especially useful if you press F2 rapidly, or if your app takes a moment to load.
        Sleep, 3000 ; Wait 3 seconds (3000 milliseconds). Adjust as needed.

        ; MsgBox, 0,, StreamingSimplifier launched. ; Optional: user feedback
    }
return