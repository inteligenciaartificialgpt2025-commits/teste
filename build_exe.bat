@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ================================================================
REM  Build do executavel do aplicativo Automacao de Janelas
REM  - Cria/atualiza um ambiente virtual local (.venv)
REM  - Instala dependencias do requirements.txt e PyInstaller
REM  - Gera o .exe em modo janela na pasta dist\AutomacaoJanelas
REM  - Usa assets\app.ico como icone se o arquivo existir
REM ================================================================

cd /d "%~dp0"

set "APP_NAME=AutomacaoJanelas"
set "ENTRYPOINT=automacao_janelas.py"
set "VENV_DIR=.venv"
set "ICON_FILE=assets\app.ico"

if not exist "%ENTRYPOINT%" (
    echo [ERRO] Arquivo principal nao encontrado: %ENTRYPOINT%
    exit /b 1
)

REM Localiza Python no Windows. O usuario final nao precisa disso; apenas a
REM maquina de build precisa ter Python para gerar o instalador.
set "PYTHON_CMD="
where py >nul 2>nul && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    where python >nul 2>nul && set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo [ERRO] Python 3 nao encontrado nesta maquina de build.
    echo Instale Python apenas no computador usado para gerar o instalador.
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Criando ambiente virtual em %VENV_DIR%...
    %PYTHON_CMD% -m venv "%VENV_DIR%" || exit /b 1
)

set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

echo [INFO] Atualizando pip...
"%VENV_PY%" -m pip install --upgrade pip || exit /b 1

echo [INFO] Instalando dependencias do projeto...
"%VENV_PY%" -m pip install -r requirements.txt || exit /b 1

echo [INFO] Instalando PyInstaller...
"%VENV_PY%" -m pip install --upgrade pyinstaller || exit /b 1

REM Limpa artefatos antigos para evitar arquivos obsoletos no instalador.
if exist "build" rmdir /s /q "build"
if exist "dist\%APP_NAME%" rmdir /s /q "dist\%APP_NAME%"
if exist "%APP_NAME%.spec" del /q "%APP_NAME%.spec"

set "ICON_ARGS="
if exist "%ICON_FILE%" (
    set "ICON_ARGS=--icon=%ICON_FILE%"
    echo [INFO] Usando icone personalizado: %ICON_FILE%
) else (
    echo [INFO] Icone personalizado nao encontrado; o executavel usara o icone padrao.
)

echo [INFO] Gerando executavel em dist\%APP_NAME%...
"%VENV_PY%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --name "%APP_NAME%" ^
    !ICON_ARGS! ^
    "%ENTRYPOINT%" || exit /b 1

echo.
echo [OK] Executavel gerado em: %CD%\dist\%APP_NAME%\%APP_NAME%.exe
echo [INFO] Agora compile installer.iss no Inno Setup para gerar o instalador final.
endlocal
