@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Deploy Macleen's Food House to Render
set "PYTHONUTF8=1"
set "DEPLOY_BRANCH=main"

echo ============================================================
echo   MACLEEN'S FOOD HOUSE - GITHUB TO RENDER DEPLOYMENT
echo ============================================================
echo.
echo This script will:
echo   1. Run the project safety checks.
echo   2. Stage and commit the current project changes.
echo   3. Push the main branch to GitHub.
echo   4. Let the connected Render service deploy that push.
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo ERROR: Git was not found.
  echo Install Git for Windows, restart VS Code, and try again.
  pause
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo ERROR: This folder is not a Git repository.
  echo.
  echo Open the GitHub-connected Macleen's project folder in VS Code,
  echo replace its contents with the update files, and put this script
  echo in that same folder before running it again.
  echo.
  echo Expected repository:
  echo https://github.com/apaciblemacky-sketch/macleens-foodhouse-pos
  pause
  exit /b 1
)

set "DEPLOY_CURRENT_BRANCH="
for /f "delims=" %%B in ('git branch --show-current') do set "DEPLOY_CURRENT_BRANCH=%%B"
if not defined DEPLOY_CURRENT_BRANCH (
  echo ERROR: Git could not identify the current branch.
  pause
  exit /b 1
)
if /i not "%DEPLOY_CURRENT_BRANCH%"=="%DEPLOY_BRANCH%" (
  echo ERROR: The current branch is "%DEPLOY_CURRENT_BRANCH%", not "%DEPLOY_BRANCH%".
  echo Switch to the main branch in VS Code before deploying.
  pause
  exit /b 1
)

set "DEPLOY_REMOTE="
for /f "delims=" %%R in ('git remote get-url origin 2^>nul') do set "DEPLOY_REMOTE=%%R"
if not defined DEPLOY_REMOTE (
  echo ERROR: This repository has no GitHub "origin" remote.
  echo Connect the folder to the Macleen's GitHub repository first.
  pause
  exit /b 1
)

if not exist "app.py" (
  echo ERROR: app.py is missing from this folder.
  pause
  exit /b 1
)
if not exist "requirements.txt" (
  echo ERROR: requirements.txt is missing from this folder.
  pause
  exit /b 1
)
if not exist "render.yaml" (
  echo ERROR: render.yaml is missing from this folder.
  pause
  exit /b 1
)
if not exist "scripts\predeploy_check.py" (
  echo ERROR: scripts\predeploy_check.py is missing.
  pause
  exit /b 1
)

set "DEPLOY_CHECK_CMD="
if exist ".venv\Scripts\python.exe" set "DEPLOY_CHECK_CMD=.venv\Scripts\python.exe"
if not defined DEPLOY_CHECK_CMD if exist ".venv_macleens\Scripts\python.exe" set "DEPLOY_CHECK_CMD=.venv_macleens\Scripts\python.exe"
if not defined DEPLOY_CHECK_CMD (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3.14 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "DEPLOY_CHECK_CMD=py -3.14"
    if not defined DEPLOY_CHECK_CMD set "DEPLOY_CHECK_CMD=py -3"
  )
)
if not defined DEPLOY_CHECK_CMD (
  where python >nul 2>&1
  if not errorlevel 1 set "DEPLOY_CHECK_CMD=python"
)
if not defined DEPLOY_CHECK_CMD (
  echo ERROR: Python was not found. Run RUN_MACLEENS.bat first.
  pause
  exit /b 1
)

echo Running pre-deployment safety checks...
%DEPLOY_CHECK_CMD% scripts\predeploy_check.py
if errorlevel 1 (
  echo.
  echo DEPLOYMENT STOPPED: Fix the reported check before pushing.
  pause
  exit /b 1
)

echo Running isolated Community and social-preview behavior checks...
%DEPLOY_CHECK_CMD% scripts\community_smoke_check.py
if errorlevel 1 (
  echo.
  echo DEPLOYMENT STOPPED: Community or social-preview behavior checks failed.
  pause
  exit /b 1
)

echo Running Financial Statements and Bundle Deals behavior checks...
%DEPLOY_CHECK_CMD% scripts\financial_bundle_smoke_check.py
if errorlevel 1 (
  echo.
  echo DEPLOYMENT STOPPED: Financial Statements or Bundle Deals checks failed.
  pause
  exit /b 1
)

echo.
echo GitHub remote:
echo %DEPLOY_REMOTE%
echo.
echo Files currently changed:
git status --short
echo.
echo IMPORTANT:
echo - .env files, virtual environments, databases, and ZIP files are
echo   excluded by the project's .gitignore and will not be pushed.
echo - This script never force-pushes.
echo - A successful push triggers Render only when Auto-Deploy is enabled
echo   for the linked main branch.
echo.

set "DEPLOY_CONFIRM="
set /p "DEPLOY_CONFIRM=Type DEPLOY to commit and push these changes: "
if /i not "%DEPLOY_CONFIRM%"=="DEPLOY" (
  echo Deployment cancelled. Nothing was pushed.
  pause
  exit /b 0
)

set "DEPLOY_MESSAGE="
set /p "DEPLOY_MESSAGE=Commit message [Update Macleen's Food House system]: "
if not defined DEPLOY_MESSAGE set "DEPLOY_MESSAGE=Update Macleen's Food House system"

echo.
echo Staging project changes...
git add -A
if errorlevel 1 (
  echo ERROR: Git could not stage the changes.
  pause
  exit /b 1
)

git diff --cached --quiet
if errorlevel 1 (
  echo Creating commit...
  git commit -m "%DEPLOY_MESSAGE%"
  if errorlevel 1 (
    echo ERROR: Git could not create the commit.
    echo Check that your Git name and email are configured.
    pause
    exit /b 1
  )
) else (
  echo No uncommitted project changes were found. Pushing current main.
)

echo.
echo Pushing main to GitHub...
git push origin "%DEPLOY_BRANCH%"
if errorlevel 1 (
  echo.
  echo DEPLOYMENT STOPPED: GitHub push failed.
  echo Sign in to GitHub when prompted, check your internet connection,
  echo and make sure you have access to the repository.
  echo No force-push was attempted.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   PUSH SUCCEEDED
echo ============================================================
echo Render should now build the latest main-branch commit.
echo Check the Render Events page until the deployment says Live.
echo.
echo Production health check:
echo https://macleens-foodhouse-pos.onrender.com/healthz
echo Expected release after Render finishes: 2026.09.05-financial-statements-v8
echo Then test one product link, both role-locked Community dashboards,
echo 25-person @mentions, cover photos, no-refresh comments, project workspaces,
echo Financial Statements, and one bundle checkout.
echo.
start "" "https://dashboard.render.com/"
start "" "https://macleens-foodhouse-pos.onrender.com/healthz"
pause
endlocal
