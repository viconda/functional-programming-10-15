@echo off
    chcp 65001 >nul
    cd /d "%~dp0"
    set PYTHONPATH=%CD%\src
    py -3 main.py
    py -3 -m pytest --cov=shop --cov-report=term-missing
    pause
