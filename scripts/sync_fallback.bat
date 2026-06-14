@echo off
REM Nakili data muhimu kutoka MySQL kwenda fallback SQLite
cd /d "%~dp0.."

echo ============================================
echo   Sync Fallback Database
echo ============================================
python manage.py sync_fallback_db --migrate-fallback
if errorlevel 1 (
    echo Sync imeshindwa. Anzisha MySQL kwenye XAMPP kwanza.
    pause
    exit /b 1
)
echo.
echo Sync imekamilika. Anzisha tena runserver ikiwa MySQL imezima.
pause
