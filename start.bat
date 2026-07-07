@echo off 
title Lancement de l'application de transcription

cd /d "%~dp0"

if not exist conda_env (
    echo [ERREUR] L'environnement Conda local est introuvable.
    echo Veuillez lancer 'installer.bat' en premier.
    pause
    exit
)

echo 1. Preparation du navigateur
:: Ouvre le navigateur en arrière-plan avec un léger différé de 3 secondes
start "" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:5000"

echo 2. Demarrage de Flask via Conda
:: 'conda run' execute l'application directement dans le bon contexte environnemental
call conda run --prefix "%~dp0conda_env" python server.py

pause