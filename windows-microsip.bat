@echo off
setlocal enabledelayedexpansion
set arg=%1
for /f "tokens=1 delims=-" %%a in ("%arg%") do set id=%%a
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "https://2511-onde.positif.ma/platform/cas-entrants/edit/!id!"
endlocal
