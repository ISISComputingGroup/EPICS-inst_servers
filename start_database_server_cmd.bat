REM @echo off
setlocal
set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%..\..\..\config_env_base.bat

%HIDEWINDOW% h
set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255
set EPICS_CA_MAX_ARRAY_BYTES=10000000
set PYTHONUNBUFFERED=TRUE
if exist "%PYTHON3W%" (
    %PYTHON3W% %MYDIRBLOCK%DatabaseServer\database_server.py -od %MYDIRBLOCK%..\..\..\iocstartup
) else (
    @echo ERROR: cannot find python via PYTHON3W environment varibale
)
