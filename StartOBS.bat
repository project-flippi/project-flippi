@echo off
echo Starting Project Flippi (OBS path via obs-websocket)...
echo -----------------------------------------------

:: -----------------------------
:: User-configurable settings
:: -----------------------------
set "OBS_PROFILE_NAME=ProjectFlippi"
set "OBS_REC_PATH=%USERPROFILE%\project-flippi-youtube\Event\GoldenCactusWeeklies\fullrecordings"

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

:: Ensure the recording directory exists
if not exist "%OBS_REC_PATH%" (
  echo Creating recording directory: "%OBS_REC_PATH%"
  mkdir "%OBS_REC_PATH%" 2>nul
)

:: Ensure Node & script exist
where node >nul 2>&1
if errorlevel 1 (
  echo ERROR: Node.js not found in PATH. Install Node.js, then try again.
  pause
  exit /b 1
)
if not exist "%SETTER_JS%" (
  echo ERROR: Script not found: "%SETTER_JS%"
  echo Make sure you saved set-rec-path.js and ran "npm install obs-websocket-js" in %SCRIPT_DIR%.
  pause
  exit /b 1
)

:: IMPORTANT: Start OBS first (so websocket is listening), then set the path.
:: If your OBS is already running with websocket enabled at startup, you can skip launching it here.
echo Launching OBS Studio (Profile: %OBS_PROFILE_NAME%) minimized...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process '%OBS_DIR%\obs64.exe' -WorkingDirectory '%OBS_DIR%' -ArgumentList @('--profile','%OBS_PROFILE_NAME%') -WindowStyle Minimized"

:: Give OBS a moment to boot the websocket server
timeout /t 10 >nul

:: Update the recording path on the target profile via websocket
echo Setting OBS recording path via obs-websocket...
node "%SETTER_JS%" "%OBS_REC_PATH%" "%OBS_PROFILE_NAME%" "%OBS_HOST%" "%OBS_PORT%" "%OBS_PASSWORD%"
if errorlevel 1 (
  echo ERROR: Could not set recording path through obs-websocket.
  echo Check OBS → Settings → WebSocket Server port/password, then try again.
  pause
  exit /b 1
)

:: Relaunch OBS with Replay Buffer (optional):
:: If OBS is already running from above, this will just bring it up with the same instance.
echo Bringing up OBS with Replay Buffer...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Start-Process 'obs64.exe' -WorkingDirectory '%OBS_DIR%' -Verb RunAs -ArgumentList @('--profile','%OBS_PROFILE_NAME%','--startreplaybuffer')"

echo Done. Recording path should now be: %OBS_REC_PATH%
pause
