@echo off

cd /d "%~dp0"

echo ==========================================
echo  1. Creation de l'environnement virtuel...
echo ==========================================

if not exist venv (
    py -3.11 -m venv venv
    echo Environnement cree !
) else (
    echo L'environnement venv existe deja.
)

echo ==========================================
echo  2. Activation et mise a jour de PIP...
echo ==========================================
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo ==========================================
echo  3. Installation des librairies...
echo ==========================================

where nvidia-smi >nul 2>&1
set DETEC_PATH=%errorlevel%

if exist "C:\Program Files\NVIDIA Corporation\Nvidia-smi\nvidia-smi.exe" (set DETEC_DIRECT=0) else (set DETEC_DIRECT=1)

if %DETEC_PATH% equ 0 (set NVIDIA_OK=1) else if %DETEC_DIRECT% equ 0 (set NVIDIA_OK=1) else (set NVIDIA_OK=0)

if %NVIDIA_OK% equ 1 (
    echo [OK] Carte NVIDIA active trouvee.
    venv\Scripts\pip install -r requirements_gpu.txt
) else (
    echo [INFO] Pas de carte NVIDIA ou pilotes absents - Repli sur CPU.
    venv\Scripts\pip install -r requirements_cpu.txt
)

echo ==========================================
echo  Installation terminee avec succes !
echo ==========================================
pause