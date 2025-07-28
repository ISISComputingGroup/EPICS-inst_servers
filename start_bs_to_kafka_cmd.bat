REM @echo off

set MYDIRCD=%~dp0
call %MYDIRCD%..\..\..\config_env_base.bat

%HIDEWINDOW% h

set EPICS_CAS_INTF_ADDR_LIST=127.0.0.1
set EPICS_CAS_BEACON_ADDR_LIST=127.255.255.255

set PYTHONUNBUFFERED=TRUE


if "%INSTRUMENT%" == "NDXHIFI" (
    set "BROKER=130.246.55.29:9092"
) else (
    set "BROKER=livedata.isis.cclrc.ac.uk:31092"
)

@echo %DATE% %TIME% starting BS to Kafka 
%PYTHON3W% %MYDIRCD%\BlockServerToKafka\main.py -d %INSTRUMENT%_sampleEnv -c %INSTRUMENT%_forwarderConfig -b %BROKER% -p %MYPVPREFIX%
