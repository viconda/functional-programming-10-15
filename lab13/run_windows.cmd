@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto ready
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -m venv .venv
    goto install
)
where python >nul 2>nul
if not errorlevel 1 (
    python -m venv .venv
    goto install
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
    "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m venv .venv
    goto install
)
echo Установите Python 3.12 и повторите запуск.
pause
exit /b 1
:install
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failure
:ready
set "PYTHONPATH=%CD%\src"
".venv\Scripts\python.exe" main.py
if errorlevel 1 goto failure
".venv\Scripts\python.exe" -m pytest --cov=analytics --cov-report=term-missing
if errorlevel 1 goto failure
echo Проверки завершены.
pause
exit /b 0
:failure
echo Ошибка запуска. Прочитайте сообщение выше.
pause
exit /b 1
