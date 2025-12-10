@echo off
REM Run tests with coverage report
echo Running tests with coverage...
C:\Users\kengupich\AppData\Local\Programs\Python\Python310\python.exe -m pytest tests/ --cov=database --cov-report=html --cov-report=term-missing

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ Tests complete! Opening coverage report...
    start htmlcov\index.html
) else (
    echo.
    echo ✗ Some tests failed!
    exit /b %ERRORLEVEL%
)
