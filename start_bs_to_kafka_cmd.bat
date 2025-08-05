setlocal

set MYDIRCD=%~dp0
call %MYDIRCD%..\..\..\config_env_base.bat
@echo on

%HIDEWINDOW% h

set "GETMACRO=%EPICS_KIT_ROOT%\support\icpconfig\master\bin\%EPICS_HOST_ARCH%\icpconfigGetMacro.exe"
set "MYIOCNAME=BSKAFKA"

set "KAFKA_BROKER=livedata.isis.cclrc.ac.uk:31092"
REM allow local config override in globals.txt
for /f %%a in ( '%GETMACRO% "KAFKA_BROKER" %MYIOCNAME%'  ) do ( set "KAFKA_BROKER=%%a" )

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set PYTHONUNBUFFERED=TRUE

@echo %DATE% %TIME% starting BS to Kafka 
%PYTHON3W% %MYDIRCD%\BlockServerToKafka\main.py -d %INSTRUMENT%_sampleEnv -r %INSTRUMENT%_runLog -c %INSTRUMENT%_forwarderConfig  -b %KAFKA_BROKER% -p %MYPVPREFIX%
