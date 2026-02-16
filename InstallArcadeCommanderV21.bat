@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Arcade Commander V21 Installer

set "SCRIPT_DIR=%~dp0"
set "DEFAULT_INSTALL_DIR=C:\ArcadeCommander\V21"
set "INSTALL_DIR=%DEFAULT_INSTALL_DIR%"
set "ZIP_FILE=%~1"

if defined ZIP_FILE (
    set "ZIP_FILE=%ZIP_FILE:"=%"
)

if not defined ZIP_FILE (
    if exist "%SCRIPT_DIR%ArcadeCommanderV21Windows.zip" (
        set "ZIP_FILE=%SCRIPT_DIR%ArcadeCommanderV21Windows.zip"
    )
)

if not defined ZIP_FILE (
    for %%F in ("%SCRIPT_DIR%*.zip") do (
        if not defined ZIP_FILE set "ZIP_FILE=%%~fF"
    )
)

echo.
echo ============================================================
echo Arcade Commander V21 Installer
echo ============================================================
echo.
if defined ZIP_FILE (
    echo Package detected:
    echo !ZIP_FILE!
) else (
    echo Package not auto-detected.
    echo You can drag and drop the ZIP onto this BAT file.
)
echo.

echo Default install location:
echo %DEFAULT_INSTALL_DIR%
set /p USE_DEFAULT=Use this location? (Y/N):
if /I "!USE_DEFAULT!"=="N" (
    set /p INSTALL_DIR=Enter install location:
    if "!INSTALL_DIR!"=="" set "INSTALL_DIR=%DEFAULT_INSTALL_DIR%"
)

echo.
echo Selected install location:
echo !INSTALL_DIR!
set /p CONFIRM=Proceed with install? (Y/N):
if /I not "!CONFIRM!"=="Y" (
    echo.
    echo Install cancelled.
    goto :end
)

if not defined ZIP_FILE (
    echo.
    echo No ZIP package found.
    echo Place the ZIP in this folder or pass it as the first argument.
    echo Example:
    echo InstallArcadeCommanderV21.bat "C:\Path\ArcadeCommanderV21Windows.zip"
    goto :end
)

where tar >nul 2>&1
if errorlevel 1 (
    echo.
    echo This system does not have the tar tool available.
    echo Please unzip manually to:
    echo !INSTALL_DIR!
    goto :end
)

if not exist "!INSTALL_DIR!" (
    mkdir "!INSTALL_DIR!" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo Failed to create install directory:
        echo !INSTALL_DIR!
        goto :end
    )
)

echo.
echo Extracting package...
tar -xf "!ZIP_FILE!" -C "!INSTALL_DIR!"
if errorlevel 1 (
    echo.
    echo Extraction failed.
    echo Verify the ZIP is valid and try again.
    goto :end
)

echo.
echo Install complete.
echo Installed to:
echo !INSTALL_DIR!
echo.
echo Recommended first run:
echo 1. Start ACLighterV2-1.exe
echo 2. Start ArcadeCommanderV2-1.exe

:end
echo.
pause
endlocal
