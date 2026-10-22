@echo off
setlocal
REM --- update.bat ---
REM Gets the latest StreamingSimplifier code from GitHub and refreshes the libraries.
REM Close the app before running this. Safe to run as often as you like.

cd /d "%~dp0"
echo.
echo === Updating StreamingSimplifier ===
echo.

where git >nul 2>nul
if errorlevel 1 goto :nogit
if not exist ".git" goto :nogit

REM --- Normal route: this folder is a git copy ---
git pull --ff-only
if errorlevel 1 goto :pullfailed
goto :libraries

:nogit
REM --- No git here: download the latest files instead.
REM     Launch.ahk and launch.bat are NOT replaced, so a customised copy on this PC is kept.
echo Git is not set up in this folder, so downloading the latest files instead...
set "TMPZ=%TEMP%\ss_update"
if exist "%TMPZ%" rmdir /s /q "%TMPZ%"
mkdir "%TMPZ%"
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest 'https://github.com/gleo-bahamas/StreamingSimplifier/archive/refs/heads/master.zip' -OutFile '%TMPZ%\s.zip'; Expand-Archive '%TMPZ%\s.zip' '%TMPZ%' -Force"
if errorlevel 1 goto :dlfailed
if not exist "%TMPZ%\StreamingSimplifier-master\main.py" goto :dlfailed
for %%F in (main.py requirements.txt Readme.md CHANGELOG.MD) do copy /y "%TMPZ%\StreamingSimplifier-master\%%F" "%~dp0%%F" >nul
rmdir /s /q "%TMPZ%"
echo Files updated: main.py, requirements.txt, Readme.md, CHANGELOG.MD

:libraries
if not exist ".venv\Scripts\python.exe" goto :novenv
echo.
echo Refreshing libraries...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :piperror
echo.
echo === Update finished. Start the app as usual. ===
echo.
pause
exit /b 0

:novenv
echo.
echo Code updated, but this folder has no .venv yet. Run install.bat once to set it up.
echo.
pause
exit /b 0

:pullfailed
echo.
echo The update was not applied. Most often this means a file in this folder was edited on
echo this PC ^(for example Launch.ahk^) and would be overwritten. Nothing was changed.
echo Read the message above, then ask for help before forcing anything.
echo.
pause
exit /b 1

:dlfailed
echo.
echo The download did not work. Check the internet connection and try again.
echo.
pause
exit /b 1

:piperror
echo.
echo The code updated but installing the libraries failed. Check the internet connection
echo and run update.bat again.
echo.
pause
exit /b 1
