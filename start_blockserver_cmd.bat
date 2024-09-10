REM @echo off
setlocal
set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%..\..\..\config_env_base.bat

%HIDEWINDOW% h

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255
set EPICS_CA_MAX_ARRAY_BYTES=1000000

set PYTHONUNBUFFERED=TRUE

set MYDIRGATE=%MYDIRBLOCK%..\..\..\gateway
if exist "%ICPSETTINGSDIR%/gwblock.pvlist" (
    set GWBLOCK_PVLIST=%ICPSETTINGSDIR%/gwblock.pvlist
) else (
    set GWBLOCK_PVLIST=%MYDIRGATE%\gwblock_dummy.pvlist
)
if exist "%PYTHON3W%" (
    %PYTHON3W% %MYDIRBLOCK%\block_server.py -od %MYDIRBLOCK%..\..\..\iocstartup -sd %MYDIRBLOCK%\schema\ -cd %ICPCONFIGROOT% -scd %ICPINSTSCRIPTROOT% -pv %GWBLOCK_PVLIST% -f ISIS
) else (
    @echo ERROR: cannot find python via PYTHON3W environment varibale
)
