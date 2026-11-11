@echo off
chcp 65001 >nul
title One-Input Git Branch, Commit & Auto PR - Land Cadastre
color 0A

echo ======================================================================
echo    SupremeAI Land-bd: One-Input Auto Branch, Commit ^& Pull Request
echo ======================================================================
echo.

:: 1. Check if git and gh CLI are available
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH!
    pause
    exit /b 1
)

where gh >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] GitHub CLI (gh) is not installed or not in PATH!
    pause
    exit /b 1
)

:: 2. Check current changes
echo [INFO] Local modified/added files:
git status --short
echo.

:: 3. Ask user for JUST ONE input
set /p USER_INPUT="Enter Task / Feature Name (e.g. khatian search speed optimization): "
if "%USER_INPUT%"=="" (
    echo [ERROR] Name cannot be empty!
    pause
    exit /b 1
)

:: 4. Convert USER_INPUT to clean branch name using PowerShell (replace spaces/special chars with hyphens)
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$name = '%USER_INPUT%'.Trim().ToLower() -replace '[^a-z0-9]+', '-'; $name.Trim('-')"`) do set CLEAN_BRANCH=%%i

if "%CLEAN_BRANCH%"=="" (
    set CLEAN_BRANCH=update-patch
)

:: Set PR Title and Commit Message exactly to what the user typed
set PR_TITLE=%USER_INPUT%
set COMMIT_MSG=%USER_INPUT%

echo.
echo ======================================================================
echo  ✓ Generated Branch : %CLEAN_BRANCH%
echo  ✓ Commit / PR Title: %PR_TITLE%
echo ======================================================================
echo.

echo [1/4] Switching to new branch '%CLEAN_BRANCH%'...
git checkout -b "%CLEAN_BRANCH%" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Branch exists, checking out...
    git checkout "%CLEAN_BRANCH%"
)

echo.
echo [2/4] Staging modified and new files...
git add .

echo.
echo [3/4] Committing changes (Running Pre-commit Security Checks)...
git commit -m "%COMMIT_MSG%"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Commit failed or rejected by security checks!
    pause
    exit /b 1
)

echo.
echo [4/4] Pushing branch '%CLEAN_BRANCH%' to GitHub...
git push -u origin "%CLEAN_BRANCH%"
if %errorlevel% neq 0 (
    echo [ERROR] Git push failed!
    pause
    exit /b 1
)

echo.
echo [INFO] Creating Pull Request against 'main'...
gh pr create --title "%PR_TITLE%" --body "Automated Pull Request for: **%PR_TITLE%**" --base main --head "%CLEAN_BRANCH%" --web=false

if %errorlevel% equ 0 (
    echo.
    echo ======================================================================
    echo  🎉 SUCCESS: Branch pushed and PR created with title:
    echo  "%PR_TITLE%"
    echo ======================================================================
) else (
    echo.
    echo [INFO] PR creation finished (or PR already exists).
)

echo.
pause
