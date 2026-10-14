@echo off
setlocal
cd /d "%~dp0"
python organiza_facil.py
if errorlevel 1 pause
