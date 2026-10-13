@echo off
rem One-off: rebuild derived files from the raw layer (Task "SRL rebuild").
set PYTHONIOENCODING=utf-8
cd /d "%~dp0..\.."
"C:\Users\tkkim\AppData\Local\Programs\Python\Python312\python.exe" scripts\acquire\finish_collection.py --rebuild-only >> "outputs\diagnostics\logs\finish_collection_console.log" 2>&1
