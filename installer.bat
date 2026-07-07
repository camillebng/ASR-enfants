@echo off
set "CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes"
title Installation de l'application de transcription

cd /d "%~dp0"

echo ==========================================
echo  Verification du systeme Conda...
echo ==========================================

:: Detection dynamique de l'emplacement de Conda
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
        echo [ERREUR] La commande 'conda' est introuvable et aucune installation par defaut n'a ete detectee.
        echo Veuillez installer Miniconda avant de lancer ce script.
        pause
        exit
    )
)

echo ==========================================
echo  1. Creation de l'environnement Conda...
echo ==========================================
if exist conda_env goto :conda_exists
call %CONDA_CMD% create --prefix "%~dp0conda_env" python=3.11 --no-default-packages -y
echo [OK] Environnement cree !
goto :ffmpeg_step

:conda_exists
echo [INFO] L'environnement local 'conda_env' existe deja.

:ffmpeg_step
echo ==========================================
echo  2. Installation de FFmpeg Statique (v6.1.1)...
echo ==========================================
echo [INFO] Telechargement de FFmpeg v6.1.1 (Archive permanente GitHub)...

:: ffmpeg en version 6.1.1 (stable pour whisperx)
call %CONDA_CMD% run --prefix "%~dp0conda_env" python -c "import urllib.request, zipfile, io, os; req=urllib.request.Request('https://github.com/GyanD/codexffmpeg/releases/download/6.1.1/ffmpeg-6.1.1-essentials_build.zip', headers={'User-Agent':'Mozilla'}); r=urllib.request.urlopen(req); z=zipfile.ZipFile(io.BytesIO(r.read())); [open(os.path.join('conda_env', 'Scripts', os.path.basename(f)), 'wb').write(z.read(f)) for f in z.namelist() if f.endswith('.exe')]"

if exist "conda_env\Scripts\ffmpeg.exe" (
    echo [OK] FFmpeg v6.1.1 configure avec succes dans l'environnement !
) else (
    echo [ERREUR] Le telechargement de FFmpeg v6.1.1 a echoue.
)

echo ==========================================
echo  3. Installation des librairies Python...
echo ==========================================
echo [INFO] Mise a jour de PIP...
call %CONDA_CMD% run --prefix "%~dp0conda_env" python -m pip install --upgrade pip

:: Verification de la presence d'une carte graphique NVIDIA
where nvidia-smi >nul 2>&1
set "DETEC_PATH=%errorlevel%"

if exist "C:\Program Files\NVIDIA Corporation\Nvidia-smi\nvidia-smi.exe" (
    set "DETEC_DIRECT=0"
) else (
    set "DETEC_DIRECT=1"
)

if "%DETEC_PATH%" equ "0" (
    set "NVIDIA_OK=1"
) else if "%DETEC_DIRECT%" equ "0" (
    set "NVIDIA_OK=1"
) else (
    set "NVIDIA_OK=0"
)

if "%NVIDIA_OK%" equ "1" (
    echo [OK] Carte NVIDIA active trouvee.
    call %CONDA_CMD% run --prefix "%~dp0conda_env" pip install -r requirements_gpu.txt
) else (
    echo [INFO] Pas de carte NVIDIA ou pilotes absents - Repli sur CPU.
    call %CONDA_CMD% run --prefix "%~dp0conda_env" pip install -r requirements_cpu.txt
)

echo ==========================================
echo  Installation terminee avec succes !
echo ==========================================
pause
exit