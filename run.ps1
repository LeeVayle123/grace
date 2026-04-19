$VENV_PYTHON = ".\.venv\Scripts\python.exe"
if (Test-Path $VENV_PYTHON) {
    Write-Host "Lancement de l'application Flask avec l'environnement virtuel..." -ForegroundColor Cyan
    & $VENV_PYTHON app.py
} else {
    Write-Error "L'environnement virtuel (.venv) est introuvable. Veuillez d'abord l'initialiser."
}
