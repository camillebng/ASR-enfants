@echo off 
title Lancement de l'application de transcription

cd /d "%~dp0"

:: 1. Verification de l'existence de l'environnement local
if not exist conda_env (
    echo [ERREUR] L'environnement Conda local est introuvable.
    echo Veuillez lancer 'installer.bat' en premier.
    pause
    exit
)

:: 2. Detection dynamique de l'emplacement de Conda
set "CONDA_CMD=conda"

where conda >nul 2>&1
if "%errorlevel%" neq "0" (
    :: Si la commande globale echoue, on cherche dans les dossiers par defaut
    if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" (
        set "CONDA_CMD=%USERPROFILE%\miniconda3\condabin\conda.bat"
    ) else if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" (
        set "CONDA_CMD=%USERPROFILE%\anaconda3\condabin\conda.bat"
    ) else if exist "%USERPROFILE%\miniforge3\condabin\conda.bat" (
        set "CONDA_CMD=%USERPROFILE%\miniforge3\condabin\conda.bat"
    ) else (
        echo [ERREUR] Impossible de localiser Conda automatiquement.
        echo Veuillez executer ce script depuis le Miniconda Prompt.
        pause
        exit
    )
)

echo 3. Preparation du navigateur
:: Ouvre le navigateur en arriere-plan avec un leger differe de 3 secondes
start "" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:5000"

echo 4. Demarrage de Flask via Conda
:: Execution dans le bon contexte environnemental grace a la variable dynamique
call %CONDA_CMD% run --prefix "%~dp0conda_env" python server.py

pause