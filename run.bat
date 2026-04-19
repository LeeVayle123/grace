@echo off
set "VENV_PYTHON=.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
    echo Lancement de l'application Flask avec l'environnement virtuel...
    "%VENV_PYTHON%" app.py
) else (
    echo L'environnement virtuel (.venv) est introuvable.
    pause
)
