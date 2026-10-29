@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py main.py & goto fin)
where python >nul 2>nul && (python main.py & goto fin)
echo No se encontro Python. Instalelo desde https://www.python.org/downloads/ marcando "Add Python to PATH".
:fin
pause
