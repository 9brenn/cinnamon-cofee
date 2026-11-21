@echo off
setlocal DisableDelayedExpansion
title CinnamonCoffee installer
echo CinnamonCoffee - install one current script copy
echo.
if not exist "%~dp0Install-CinnamonCoffee.ps1" (
  echo ERROR: Keep this CMD file beside Install-CinnamonCoffee.ps1.
  pause
  exit /b 1
)
set "gameFolder=%~1"
if not defined gameFolder if exist "D:\Steam\steamapps\common\Grand Theft Auto V\GTA5.exe" set "gameFolder=D:\Steam\steamapps\common\Grand Theft Auto V"
if not defined gameFolder if exist "D:\Steam\steamapps\common\Grand Theft Auto V\GTA5_Enhanced.exe" set "gameFolder=D:\Steam\steamapps\common\Grand Theft Auto V"
if not defined gameFolder set /p "gameFolder=GTA V folder (the folder containing GTA5.exe): "
set "gameFolder=%gameFolder:"=%"
if not defined gameFolder (
  echo ERROR: No game folder was supplied.
  pause
  exit /b 1
)
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-CinnamonCoffee.ps1" -GameFolder "%gameFolder%"
set "installExit=%ERRORLEVEL%"
echo.
if "%installExit%"=="0" (
  echo Installation completed. Start GTA V again and check the version in the menu.
) else (
  echo Installation failed. Read the error above before starting GTA V.
)
pause
exit /b %installExit%
