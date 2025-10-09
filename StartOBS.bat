@echo off
setlocal EnableExtensions EnableDelayedExpansion
echo Starting Project Flippi (OBS path via obs-websocket)...
echo -----------------------------------------------

:: -----------------------------
:: User-configurable settings
:: -----------------------------
set "OBS_PROFILE_NAME=ProjectFlippi"
:: initial default (will be overwritten after selection)
set "OBS_REC_PATH=%USERPROFILE%\project-flippi-youtube\Event\Hokie-Hoedown\fullrecordings"

:: obs-websocket connection (match OBS settings)
set "OBS_HOST=127.0.0.1"
set "OBS_PORT=4444"
set "OBS_PASSWORD=REDACTED"

:: -----------------------------
:: Paths
:: -----------------------------
set "OBS_DIR=%ProgramFiles%\obs-studio\bin\64bit"
set "SCRIPT_DIR=%USERPROFILE%\project-flippi-youtube"
set "SETTER_JS=%SCRIPT_DIR%\set-rec-path.js"
set "EVENTS_DIR=%USERPROFILE%\project-flippi-youtube\Event"

:: -----------------------------
:: Pick an Event folder
:: -----------------------------
if not exist "%EVENTS_DIR%" (
  echo ERROR: Events directory not found: "%EVENTS_DIR%"
  echo Create it and subfolders first.
  pause
  exit /b 1
)

set "idx=0"
for /d %%D in ("%EVENTS_DIR%\*") do (
  set /a idx+=1
  set "EVT_!idx!=%%~nxD"
)

if %idx%==0 (
  echo ERROR: No event folders found inside "%EVENTS_DIR%".
  echo Create one e.g. GoldenCactusWeeklies and try again.
  pause
  exit /b 1
)

echo Available events:
REM Use CALL indirection to expand EVT_%%N variables
for /l %%N in (1,1,%idx%) do call echo  %%N %%EVT_%%N%%
echo.

:ASK_EVENT
set "choice="
set /p "choice=Enter the number of the event to record for: "

:: Validate numeric
set "nonnum="
for /f "delims=0123456789" %%A in ("%choice%") do set "nonnum=%%A"
if defined nonnum (
  echo Invalid selection: "%choice%". Please enter a number 1-%idx%.
  goto ASK_EVENT
)
if "%choice%"=="" (
  echo Please enter a number 1-%idx%.
  goto ASK_EVENT
)
if %choice% lss 1 (
  echo Number out of range. Choose 1-%idx%.
  goto ASK_EVENT
)
if %choice% gtr %idx% (
  echo Number out of range. Choose 1-%idx%.
  goto ASK_EVENT
)

REM Resolve EVT_%choice% safely
call set "EVENT_NAME=%%EVT_%choice%%%"
set "OBS_REC_PATH=%EVENTS_DIR%\%EVENT_NAME%\fullrecordings"

echo Selected event: "%EVENT_NAME%"
echo Recording folder: "%OBS_REC_PATH%"
echo.

:: Ensure the recording directory exists
if not exist "%OBS_REC_PATH%" (
  echo Creating recording directory: "%OBS_REC_PATH%"
  mkdir "%OBS_REC_PATH%" 2>nul
)

:: -----------------------------
:: Ensure Node & script exist
:: -----------------------------
where node >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js not found in PATH. Install Node.js, then try again.
  pause
  exit /b 1
)
if not exist "%SETTER_JS%" (
  echo ERROR: Script not found: "%SETTER_JS%"
  echo Make sure you saved set-rec-path.js and ran "npm install obs-websocket-js@4" in %SCRIPT_DIR%.
  pause
  exit /b 1
)

:: -----------------------------
:: Launch OBS once (no admin), correct working dir
:: -----------------------------
echo Launching OBS Studio (Profile: %OBS_PROFILE_NAME%) minimized...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process '%OBS_DIR%\obs64.exe' -WorkingDirectory '%OBS_DIR%' -ArgumentList @('--profile','%OBS_PROFILE_NAME%') -WindowStyle Minimized"

:: Give OBS a moment to boot the websocket server
timeout /t 5 >nul

:: Update the recording path (and start Replay Buffer) via websocket
echo Setting OBS recording path via obs-websocket...
node "%SETTER_JS%" "%OBS_REC_PATH%" "%OBS_PROFILE_NAME%" "%OBS_HOST%" "%OBS_PORT%" "%OBS_PASSWORD%"
if errorlevel 1 (
  echo ERROR: Could not set recording path through obs-websocket.
  echo Check OBS ^> Tools ^> WebSocket Server Settings port/password, then try again.
  pause
  exit /b 1
)

echo Done. Recording path should now be: %OBS_REC_PATH%
pause
