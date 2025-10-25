@echo off
echo Finding process using port 8000...
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Found process ID: %%a
    echo Stopping process...
    taskkill /PID %%a /F
    echo.
    echo Process stopped successfully!
    echo You can now run: python app/main.py
    goto :end
)

echo No process found using port 8000
echo You can now run: python app/main.py

:end
pause
