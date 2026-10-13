@echo off
rem One-off: finish MOFA/MOTIR downloads, then rebuild all derived files (Task "SRL finish corpus").
set PYTHONIOENCODING=utf-8
cd /d "%~dp0..\.."
"C:\Users\tkkim\AppData\Local\Programs\Python\Python312\python.exe" scripts\acquire\finish_collection.py >> "outputs\diagnostics\logs\finish_collection_console.log" 2>&1
