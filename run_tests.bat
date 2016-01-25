set PYTHON_EXE=c:\Python27\python.exe
set MYPVPREFIX=TEST

 
REM Run the blockserver tests
cd .\BlockServer
%PYTHON_EXE% run_tests.py -o ..\..\..\test-reports

REM Run the databaseServer tests
cd .\DatabaseServer
%PYTHON_EXE% run_tests.py -o ..\..\..\test-reports