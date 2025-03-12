@echo off
REM to make this launchable from the taskbar
REM make a shortcut, then add cmd /c at the beginning
REM then pin to taskbar.
cd /d "C:\Users\troy\tws-python-balances\venv\Scripts"
call activate
cd /d "C:\Users\troy\tws-python-balances"
python myclient.py
pause
