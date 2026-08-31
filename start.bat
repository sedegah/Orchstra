@echo off
title Orchestra - UG Exam Timetable
echo.
echo  Starting Orchestra...
echo  Open your browser at: http://localhost:8000
echo.
cd /d "%~dp0"
"C:\Users\kimat\Orchstra\.venv\Scripts\python.exe" manage.py runserver 8000
pause
