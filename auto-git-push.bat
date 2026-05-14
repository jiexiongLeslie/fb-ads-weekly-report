@echo off
chcp 65001 >nul
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 exit /b 1

for /f "tokens=*" %%b in ('git branch --show-current') do set BRANCH=%%b
if "%BRANCH%"=="" set BRANCH=main

for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set TODAY=%%a-%%b-%%c
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set NOW=%%a:%%b
set COMMIT_MSG=Auto update %TODAY% %NOW%

git add -A -- . ":(exclude)user_config.json" >nul 2>&1
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "%COMMIT_MSG%" >nul 2>&1
    if errorlevel 1 exit /b 1
    git push -u origin "%BRANCH%" >nul 2>&1
    if errorlevel 1 exit /b 1
)

exit /b 0
