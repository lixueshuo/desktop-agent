@echo off
cd /d "%~dp0"
pythonw desktop.py
if errorlevel 1 pause
