echo OFF
setlocal enabledelayedexpansion

REM In the archive, find the most recent cycle folder to be created, to be used at the end of this file
for /f "delims=" %%i in ('dir "\\isis.cclrc.ac.uk\inst$\%COMPUTERNAME%\Instrument\data\" /b /ad-h /t:c /od') do set cycle_folder=%%i

REM This gets us every file in C:\data\*\bluesky_scans\
for /r C:\data\ %%i in (bluesky_scans\*) do (

    REM However, we need to check if this is C:\data\export only\[run]\bluesky_scans
    for %%j in ("%%~dpi\..\..") do (

        REM and exclude all the files already in export only
        if NOT "%%~nxj" == "export only" (

            REM We now run attrib on each of the files to find out if they're read only, andly only continue if they are
            REM We check using the parsers for set, thankfully the characteer we need is at a fixed position in the response
            for /f "usebackq tokens=*" %%k in (`attrib "%%~fi"`) do (
                set attrib_str=%%k
                set readonly_flag=!attrib_str:~5,1!

                if !readonly_flag! == R (

                    REM For the next part, we'll need the folder above bluesky_scans for the run number
                    for %%l in ("%%~dpi\..") do (

                        REM Robocopy over to export only, ignoring if the file is in any way already there
                        robocopy "%%~dpi " "C:\data\export only\%%~nxl\bluesky_scans " "%%~nxi" /mt /z /xc /xn /xo

                        REM Only if the file was copied (not skipped), try to move to the isis archive too
                        if !ERRORLEVEL! == 1 (

                            REM And copy across into this cycle's archive
                            robocopy "%%~dpi " "\\isis.cclrc.ac.uk\inst$\%COMPUTERNAME%\Instrument\data\%cycle_folder%\autoreduced\bluesky_scans\%%~nxl " "%%~nxi" /mt /z /xc /xn /xo
                        )
                    )
                )
            )
        )
    )
)
