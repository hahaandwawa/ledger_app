@echo off
chcp 65001 >nul
:: ====================================
:: 个人记账软件 - Windows 启动脚本
:: 双击此文件即可启动软件
:: ====================================

title 个人记账软件

:: 获取脚本所在目录
cd /d "%~dp0"

echo.
echo 🚀 正在启动记账软件...
echo.

:: 检查虚拟环境是否存在
if not exist "venv" (
    echo ⚠️  首次运行，正在安装必要组件...
    echo    这可能需要几分钟，请耐心等待...
    echo.
    
    :: 创建虚拟环境
    python -m venv venv
    
    if errorlevel 1 (
        echo.
        echo ❌ 错误：无法创建虚拟环境
        echo.
        echo 请确保已安装 Python 3：
        echo   1. 访问 https://www.python.org/downloads/
        echo   2. 下载并安装 Python 3
        echo   3. 安装时务必勾选 "Add Python to PATH"
        echo   4. 重新运行此脚本
        echo.
        pause
        exit /b 1
    )
    
    :: 激活虚拟环境并安装依赖
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    
    if errorlevel 1 (
        echo.
        echo ❌ 错误：安装依赖失败
        echo 请检查网络连接后重试
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo ✅ 安装完成！
    echo.
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 启动软件
echo 💰 记账软件启动中...
python src\ledger\main.py

:: 如果软件异常退出，显示提示
if errorlevel 1 (
    echo.
    echo ⚠️  软件已退出
    pause
)

