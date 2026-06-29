@echo off 
title Lancement de l'application de transcription

echo 1. Navigation vers le dossier projet 
cd /d "%~dp0"

echo 2. Activation de l'environnement virtuel
call "venv\Scripts\activate.bat"

echo 3. Préparation du navigateur
start http://127.0.0.1:5000

echo 4. Démarrage de Flask 
python server.py

pause