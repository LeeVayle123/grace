# Create a deployable ZIP of the project root
# Usage: run from project root or double-click this script

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

Write-Output "Creating deploy.zip from $root"
if (Test-Path "$root\deploy.zip") {
    Remove-Item "$root\deploy.zip" -Force
}

# Exclude typical local-only folders
$exclude = @('.git','venv','.venv','node_modules')
$items = Get-ChildItem -Path $root -Force | Where-Object { $exclude -notcontains $_.Name }

# Compress selected items
Compress-Archive -LiteralPath ($items | ForEach-Object { $_.FullName }) -DestinationPath "$root\deploy.zip" -Force

Write-Output "deploy.zip created at: $root\deploy.zip"