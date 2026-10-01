@echo off
cd /d "%~dp0"
py -3 pdfa_lote.py
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar. Instale o Python 3 para Windows e tente novamente.
  pause
)
