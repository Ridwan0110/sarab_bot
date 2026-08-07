@ECHO OFF

REM Get the directory of this script
SET "SCRIPT_DIR=%~dp0"

REM Activate venv
IF EXIST "%SCRIPT_DIR%pyvenv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%pyvenv\Scripts\activate.bat"
)

REM Execute Python script
python server.py
