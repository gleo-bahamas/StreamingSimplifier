#Persistent
F2:: ; Define action for F2 key
    ; Define the path to your launch batch file
    ; IMPORTANT: Make sure 'launch.bat' exists in this directory
    launchBatchFile := "C:\Users\admin\StreamingSimplifier\launch.bat"
    pythonScriptPath := "C:\Users\admin\StreamingSimplifier\main.py"

    ; Check if main.py is running under a python.exe process
    ; Note: This check will find *any* python.exe running your specific main.py.
    ; It doesn't specifically check if it's running in the venv's python.exe,
    ; but it's generally sufficient for preventing duplicate launches of *this* script.
    RunWait, %ComSpec% /c wmic process where "name='python.exe'" get CommandLine | find "%pythonScriptPath%",, Hide
    
    if ErrorLevel ; If WMIC finds no matching process (ErrorLevel is set), then it's not running
    {
        ; Launch the program using the batch file, which activates the venv
        ; The 'Hide' option will hide the command prompt window that the batch file opens.
        Run, "%launchBatchFile%",, Hide
    }
    return