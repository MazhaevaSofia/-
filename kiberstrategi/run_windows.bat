@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python не найден. Установите Python 3.11 или новее с python.org и отметьте галочку Add Python to PATH
  pause
  exit /b 1
)
python -m pip install --quiet pygame numpy
python main.py
if errorlevel 1 pause
