@echo off
REM MGOWELO AMCOS - Backup ya database (XAMPP / Windows)
cd /d "%~dp0.."

set MYSQL_DUMP=C:\xampp\mysql\bin\mysqldump.exe
if exist "%MYSQL_DUMP%" (
    set MYSQL_DUMP_BIN=%MYSQL_DUMP%
)

echo ============================================
echo   MGOWELO AMCOS - Database Backup
echo ============================================
echo.

python manage.py backup_database
if errorlevel 1 (
    echo.
    echo BACKUP IMESHINDWA. Hakikisha:
    echo   1. XAMPP MySQL inaendesha
    echo   2. Virtualenv imewashwa na Django imesakinishwa
    echo   3. .env ina DB_USER, DB_PASSWORD, DB_NAME sahihi
    pause
    exit /b 1
)

echo.
echo Backup imekamilika. Angalia folda: backups\
pause
