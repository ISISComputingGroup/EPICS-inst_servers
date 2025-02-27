@echo off
setlocal
set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%..\..\..\config_env_base.bat

%HIDEWINDOW% h

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

call %MYDIRBLOCK%activate_virtual_env.bat

set PYTHONUNBUFFERED=TRUE

%PYTHON3W% %MYDIRBLOCK%ArchiverAccess\archiver_access.py
