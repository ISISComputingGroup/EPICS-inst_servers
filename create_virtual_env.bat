if "%ICP_CONFIG_ENV_RUN%" == "" (
    call C:\Instrument\Apps\EPICS\config_env.bat
) else (
    @echo Using existing EPICS_ROOT %EPICS_ROOT%
)
del /q /s .venv >NUL 2>&1
%PYTHON3% -m venv .venv
call "%~dp0.venv\Scripts\activate.bat"
"%~dp0.venv\Scripts\pip.exe" install -r requirements.txt
