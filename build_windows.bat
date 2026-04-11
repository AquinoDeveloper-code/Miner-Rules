@echo off
setlocal

cd /d "%~dp0"

if not exist .venv-win\Scripts\activate.bat (
    py -3 -m venv .venv-win
)

.venv-win\Scripts\python.exe -m pip install --upgrade pip
.venv-win\Scripts\python.exe -m pip install -r requirements-build.txt
.venv-win\Scripts\python.exe -m PyInstaller --noconfirm --clean eternal_mine.spec

echo.
echo Build concluido.
echo Executavel: dist\MinaDosEscravosEternos.exe

endlocal
