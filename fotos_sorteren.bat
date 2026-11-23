@echo off
setlocal
title Fotos sorteren
rem Vind python  ^  start het sorteer-script

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo Python is niet gevonden op deze computer.
    echo Installeer het van https://www.python.org/downloads/
    echo en vink tijdens de installatie "Add Python to PATH" aan.
    echo.
    pause
    exit /b 1
)

python -c "import PIL, torch, transformers" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Eenmalige voorbereiding: benodigde packages installeren.
    echo Dit kan enkele minuten duren. Er is internetverbinding nodig.
    echo.
    python -m pip install --upgrade pip
    python -m pip install pillow pillow-heif
    python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    python -m pip install transformers
    if errorlevel 1 (
        echo.
        echo Installeren is mislukt. Controleer je internetverbinding en
        echo probeer het opnieuw.
        pause
        exit /b 1
    )
)

echo.
echo ============================================
echo   FOTO'S SORTEREN - dubbele eruit, per maand
echo ============================================
echo.
set /p FOTOMAP=Waar staan je fotos? (sleep de map hierheen en druk op Enter):
echo.
set /p KIEZEN=Eerst alleen bekijken wat er gaat gebeuren, zonder verplaatsen? (j/n):
if /i "%KIEZEN%"=="j" set MODUS=--droog
if /i not "%KIEZEN%"=="j" set MODUS=--uitvoeren

echo.
python "%~dp0sorteer_fotos.py" --bron "%FOTOMAP:"=%" %MODUS%
echo.
pause
