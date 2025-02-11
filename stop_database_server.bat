@echo off
setlocal
set MYDIR=%~dp0
REM kill procservs that manage process, which in turn terminates the process

set CSPID=
if exist "c:\instrument\var\run\EPICS_DBSVR.pid" (
    for /F %%i in ( c:\instrument\var\run\EPICS_DBSVR.pid ) DO set CSPID=%%i
)
if "%CSPID%" == "" (
    @echo %DATE% %TIME% dbserver procServ is not running
) else (
    @echo %DATE% %TIME% Killing dbserver procServ cygwin PID %CSPID%
    %ICPCYGBIN%\kill.exe %CSPID%
    del c:\instrument\var\run\EPICS_DBSVR.pid
)

