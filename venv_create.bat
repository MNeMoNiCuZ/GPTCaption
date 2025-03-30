@echo off
setlocal enabledelayedexpansion

:: Initialize counter
set COUNT=0

:: Directly parse the output of `py -0p` to get versions and their paths
for /f "tokens=1,*" %%a in ('py -0p') do (
    :: Filter lines that start with a dash, indicating a Python version, and capture the path
    echo %%a | findstr /R "^[ ]*-" > nul && (
        set /a COUNT+=1
        set "PYTHON_VER_!COUNT!=%%a"
        set "PYTHON_PATH_!COUNT!=%%b"  :: Store the path in a separate variable
        echo !COUNT!. %%a at %%b
    )
)

:: Make sure at least one Python version was found
if %COUNT%==0 (
    echo No Python installations found via Python Launcher. Exiting.
    goto end
)

:: Prompt user to select a Python version (default is 1)
set /p PYTHON_SELECTION="Select a Python version by number (Press Enter for default = '1'): "
if "!PYTHON_SELECTION!"=="" set PYTHON_SELECTION=1

:: Extract the selected Python version tag and parse the version number more accurately
set SELECTED_PYTHON_VER=!PYTHON_VER_%PYTHON_SELECTION%!

:: The version string is expected to be in the format "-V:X.Y *"
:: We'll use a for loop to extract just the "X.Y" part
for /f "tokens=2 delims=: " %%i in ("!SELECTED_PYTHON_VER!") do (
    set "SELECTED_PYTHON_VER=%%i"
)

:: Confirm the selected Python version
echo Using Python version %SELECTED_PYTHON_VER%

:: Prompt for virtual environment name with default 'venv'
set VENV_NAME=venv
set /p VENV_NAME="Enter the name for your virtual environment (Press Enter for default 'venv'): "
if "!VENV_NAME!"=="" set VENV_NAME=venv

:: Create the virtual environment using the selected Python version
echo Creating virtual environment named %VENV_NAME%...
py -%SELECTED_PYTHON_VER% -m venv %VENV_NAME%

:: Generate the venv_activate.bat file
echo Generating venv_activate.bat...
(
echo @echo off
echo cd %%~dp0
echo set VENV_PATH=%VENV_NAME%
echo.
echo echo Activating virtual environment...
echo call "%%VENV_PATH%%\Scripts\activate"
echo echo Virtual environment activated.
echo cmd /k
) > venv_activate.bat

:: Generate the venv_update.bat file for a one-time pip upgrade
echo Generating venv_update.bat for a one-time pip upgrade...
(
echo @echo off
echo cd %%~dp0
echo echo Activating virtual environment %VENV_NAME% and upgrading pip...
echo call "%VENV_NAME%\Scripts\activate"
echo python -m pip install --upgrade pip
echo echo Pip has been upgraded in the virtual environment %VENV_NAME%.
echo echo To deactivate, manually type 'deactivate'.
echo cmd /k
) > venv_update.bat

:: Ask the user if they want to upgrade pip now
echo.
set /p UPGRADE_NOW="Do you want to upgrade pip now? (Y/N) (Press Enter for default 'Y'): "
if not defined UPGRADE_NOW set UPGRADE_NOW=Y
if /I "%UPGRADE_NOW%"=="Y" (
    echo Upgrading pip and activating the virtual environment...
    call venv_update.bat
) else (
    echo Activating the virtual environment without upgrading pip...
    call venv_activate.bat
)

echo Setup complete. Your virtual environment is ready.

:: After completing the main part of the script, jump to cleanup
goto cleanup

:cleanup
:: Clean up
echo Cleanup complete.

:: End of script
endlocal
