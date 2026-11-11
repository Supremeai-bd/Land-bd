@echo off
chcp 65001 >nul
title Auto Branch, Commit & Create PR - Land Cadastre
color 0A

echo ======================================================================
echo    SupremeAI Land-bd: Automated Git Branch, Commit ^& Pull Request
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
echo [INFO] Checking local changes...
git status --short
echo.

:: 3. Ask user for branch name
set /p BRANCH_NAME="Enter New Branch Name (e.g. feat-mapping-audit or hotfix-ui): "
if "%BRANCH_NAME%"=="" (
    echo [ERROR] Branch name cannot be empty!
    pause
    exit /b 1
)

:: 4. Ask user for commit message / PR title
set /p COMMIT_MSG="Enter Commit Message / PR Title: "
if "%COMMIT_MSG%"=="" (
    set COMMIT_MSG=Update: %BRANCH_NAME% changes
)

echo.
echo ======================================================================
echo  Branch : %BRANCH_NAME%
echo  Commit : %COMMIT_MSG%
echo ======================================================================
echo.
echo [1/4] Creating and switching to branch '%BRANCH_NAME%'...
git checkout -b "%BRANCH_NAME%"
if %errorlevel% neq 0 (
    echo [WARNING] Branch might already exist, switching to it...
    git checkout "%BRANCH_NAME%"
)

echo.
echo [2/4] Staging modified and new files...
git add .

echo.
echo [3/4] Committing changes...
git commit -m "%COMMIT_MSG%"

echo.
echo [4/4] Pushing branch to GitHub and creating Pull Request...
git push -u origin "%BRANCH_NAME%"
if %errorlevel% neq 0 (
    echo [ERROR] Git push failed! Please check your internet or repo permissions.
    pause
    exit /b 1
)

echo.
echo Creating Pull Request against 'main'...
gh pr create --title "%COMMIT_MSG%" --body "Automated PR created from branch `%BRANCH_NAME%` via Auto-PR tool." --base main --head "%BRANCH_NAME%" --web=false

if %errorlevel% equ 0 (
    echo.
    echo ======================================================================
    echo  🎉 SUCCESS: Branch pushed and Pull Request created successfully!
    echo ======================================================================
) else (
    echo.
    echo [INFO] A PR might already exist for this branch or check URL above.
)

echo.
pause
