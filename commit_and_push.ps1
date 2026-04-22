<#
Commit and push templates/static and app changes to remote.
Usage:
  .\commit_and_push.ps1 [-RemoteUrl "https://github.com/you/repo.git"]

This script requires Git to be installed.
#>
param(
    [string]$RemoteUrl
)

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git not found in PATH. Install Git and re-run this script."; exit 1
}

Set-Location $PSScriptRoot

# Initialize if not a git repo
$insideRepo = $null
try { $insideRepo = git rev-parse --is-inside-work-tree 2>$null } catch { $insideRepo = $null }
if ($LASTEXITCODE -ne 0) {
    Write-Output "No git repo found — initializing repository."
    git init
    if ($RemoteUrl) {
        git remote add origin $RemoteUrl
    }
}

# Ensure branch name
try { git branch --show-current 2>$null | Out-Null } catch {}

# Stage and commit
git add templates static app.py || Write-Output "Some paths may be missing; staged what exists."

# Create a commit
$commitMsg = "Fix: add templates/static and fallback accueil.html"
git commit -m "$commitMsg" -a || Write-Output "No changes to commit or commit failed."

# Push (attempt)
if ($RemoteUrl) { git branch -M main; git push -u origin main } else { git push }

Write-Output "Done (check output above for errors)."