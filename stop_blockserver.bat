@echo off
setlocal
set MYDIR=%~dp0
REM kill procservs that manage process, which in turn terminates the process

set CSPID=
for /F %%i in ( c:\instrument\var\run\EPICS_BLOCKSVR.pid ) DO set CSPID=%%i
if "%CSPID%" == "" (
    @echo blockserver procServ is not running
) else (
    @echo Killing blockserver procServ PID %CSPID%
    %ICPCYGBIN%\kill.exe %CSPID%
    del c:\instrument\var\run\EPICS_BLOCKSVR.pid
)

