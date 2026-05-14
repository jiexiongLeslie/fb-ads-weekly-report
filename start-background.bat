@echo off
chcp 65001 >nul
cd /d "%~dp0"

wscript.exe //B //Nologo "%~dp0start-background.vbs"
