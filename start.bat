@echo off
setlocal

REM 切换到 start.bat 所在目录
cd /d "%~dp0"

REM 如果同目录没有 venv 文件夹，则创建
if not exist "venv\" (
    echo [INFO] venv not found, creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo [INFO] venv already exists, skip creation.
)

REM 进入虚拟环境
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    exit /b 1
)

REM 安装 requirements.txt 中的依赖
echo [INFO] Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)

REM 执行测试
echo [INFO] Running tests\test_all.py...
python tests\test_all.py
if errorlevel 1 (
    echo [ERROR] Tests failed.
    exit /b 1
)

echo [INFO] Done.
exit /b 0