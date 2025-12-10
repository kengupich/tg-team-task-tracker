@echo off
REM Run all tests for the project
echo Running all tests...
C:\Users\kengupich\AppData\Local\Programs\Python\Python310\python.exe -m pytest tests/ -v

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ All tests passed!
) else (
    echo.
    echo ✗ Some tests failed!
    exit /b %ERRORLEVEL%
)
