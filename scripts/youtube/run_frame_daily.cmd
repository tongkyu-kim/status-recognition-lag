@echo off
rem Daily YouTube frame collection (Windows Task "SRL YouTube frame daily", 17:15 Korea time).
rem Disables its own task when the frame is complete (scripts/youtube/run_frame.py --task-name).
set PYTHONIOENCODING=utf-8
cd /d "%~dp0..\.."
"C:\Users\tkkim\AppData\Local\Programs\Python\Python312\python.exe" scripts\youtube\run_frame.py collect --task-name "SRL YouTube frame daily" >> "outputs\diagnostics\logs\frame_daily_console.log" 2>&1
