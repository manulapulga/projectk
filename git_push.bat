@echo off
setlocal

:: GitHub repository URL
set REPO_URL=https://github.com/manulapulga/projectk.git

:: Main branch
set BRANCH=main

:: Initialize the Git repo if needed
if not exist ".git" (
    echo Initializing new Git repo...
    git init
    git remote add origin %REPO_URL%
)

:: Add all files
git add .

:: Commit with timestamp
git commit -m "Initial commit %date% %time%"

:: Push to GitHub
git push -u origin %BRANCH%

echo.
echo All done—project pushed to GitHub!
pause
