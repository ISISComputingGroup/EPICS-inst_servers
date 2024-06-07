REM @echo off
setlocal
set MYDIRBLOCK=%~dp0
call %MYDIRBLOCK%stop_database_server.bat
set CYGWIN=nodosfilewarning
call %MYDIRBLOCK%..\..\..\config_env_base.bat

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255
set EPICS_CA_MAX_ARRAY_BYTES=10000000
set IOCLOGROOT=%ICPVARDIR%/logs/ioc
for /F "usebackq" %%I in (`%ICPCYGBIN%\cygpath %IOCLOGROOT%`) do SET IOCCYGLOGROOT=%%I

set DBSERVER_CONSOLEPORT=9009

@echo Starting dbserver (console port %DBSERVER_CONSOLEPORT%)
set DBSERVER_CMD=%MYDIRBLOCK%start_database_server_cmd.bat

REM Unlike IOC we are not using "--noautorestart --wait" so gateway will start immediately and also automatically restart on exit

%ICPCYGBIN%\procServ.exe --logstamp --logfile="%IOCCYGLOGROOT%/DBSVR-%%Y%%m%%d.log" --timefmt="%%c" --restrict --ignore="^D^C" --name=DBSVR --pidfile="/cygdrive/c/instrument/var/run/EPICS_DBSVR.pid" %DBSERVER_CONSOLEPORT% %DBSERVER_CMD% 
