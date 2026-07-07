@echo off
cd /d "%~dp0"

echo ==========================================
echo  Verification du systeme Conda...
echo ==========================================
where conda >nul 2>&1
if "%errorlevel%" neq "0" goto :err_conda

echo ==========================================
echo  1. Creation de l'environnement Conda...
echo ==========================================
if exist conda_env goto :conda_exists
call conda create --prefix "%~dp0conda_env" python=3.11 --no-default-packages -y
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
call conda run --prefix "%~dp0conda_env" python -c "import urllib.request, zipfile, io, os; req=urllib.request.Request('https://github.com/GyanD/codexffmpeg/releases/download/6.1.1/ffmpeg-6.1.1-essentials_build.zip', headers={'User-Agent':'Mozilla'}); r=urllib.request.urlopen(req); z=zipfile.ZipFile(io.BytesIO(r.read())); [open(os.path.join('conda_env', 'Scripts', os.path.basename(f)), 'wb').write(z.read(f)) for f in z.namelist() if f.endswith('.exe')]"

if exist "conda_env\Scripts\ffmpeg.exe" (
    echo [OK] FFmpeg v6.1.1 configure avec succes dans l'environnement !
) else (
    echo [ERREUR] Le telechargement de FFmpeg v6.1.1 a echoue.
)

echo ==========================================
echo  3. Installation des librairies Python...
echo ==========================================
echo [INFO] Mise a jour de PIP...
call conda run --prefix "%~dp0conda_env" python -m pip install --upgrade pip

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
    call conda run --prefix "%~dp0conda_env" pip install -r requirements_gpu.txt
) else (
    echo [INFO] Pas de carte NVIDIA ou pilotes absents - Repli sur CPU.
    call conda run --prefix "%~dp0conda_env" pip install -r requirements_cpu.txt
)

echo ==========================================
echo  Installation terminee avec succes !
echo ==========================================
pause
exit

:err_conda
echo [ERREUR] La commande 'conda' est introuvable.
echo Veuillez executer ce script depuis l'Anaconda Prompt (ou Miniconda).
pause
exit