@echo off
chcp 65001 >nul
:: ====================================
:: 在桌面创建记账软件快捷方式 (Windows)
:: 带有自定义图标
:: ====================================

title 创建桌面快捷方式

echo.
echo 📁 正在创建桌面快捷方式（带自定义图标）...
echo.

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "LAUNCH_SCRIPT=%SCRIPT_DIR%启动记账软件.bat"
set "ICON_PNG=%SCRIPT_DIR%src\ledger\resources\icon.png"
set "ICON_ICO=%SCRIPT_DIR%src\ledger\resources\icon.ico"
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\记账软件.lnk"

:: 检查启动脚本是否存在
if not exist "%LAUNCH_SCRIPT%" (
    echo ❌ 错误：找不到启动脚本
    echo    请确保 '启动记账软件.bat' 文件存在
    pause
    exit /b 1
)

:: 检查是否有 ICO 图标文件
if exist "%ICON_ICO%" (
    set "USE_ICON=%ICON_ICO%"
    echo 🎨 使用自定义图标：%ICON_ICO%
) else (
    :: 尝试使用 PowerShell 将 PNG 转换为 ICO
    if exist "%ICON_PNG%" (
        echo 🎨 正在转换图标格式 PNG -^> ICO ...
        
        powershell -ExecutionPolicy Bypass -Command ^
            "$png = '%ICON_PNG%'; $ico = '%ICON_ICO%'; " ^
            "Add-Type -AssemblyName System.Drawing; " ^
            "try { " ^
            "  $img = [System.Drawing.Image]::FromFile($png); " ^
            "  $icon = [System.Drawing.Icon]::FromHandle($img.GetHicon()); " ^
            "  $fs = [System.IO.File]::Create($ico); " ^
            "  $icon.Save($fs); " ^
            "  $fs.Close(); " ^
            "  $icon.Dispose(); " ^
            "  $img.Dispose(); " ^
            "  Write-Host '图标转换成功！'; " ^
            "} catch { " ^
            "  Write-Host '图标转换失败：' $_.Exception.Message; " ^
            "}"
        
        if exist "%ICON_ICO%" (
            set "USE_ICON=%ICON_ICO%"
        ) else (
            set "USE_ICON="
            echo ⚠️  图标转换失败，将使用默认图标
        )
    ) else (
        set "USE_ICON="
        echo ⚠️  找不到图标文件，将使用默认图标
    )
)

echo.

:: 使用 PowerShell 创建快捷方式（带图标）
if defined USE_ICON (
    powershell -ExecutionPolicy Bypass -Command ^
        "$WshShell = New-Object -ComObject WScript.Shell; " ^
        "$Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); " ^
        "$Shortcut.TargetPath = '%LAUNCH_SCRIPT%'; " ^
        "$Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; " ^
        "$Shortcut.Description = '个人记账软件'; " ^
        "$Shortcut.IconLocation = '%USE_ICON%,0'; " ^
        "$Shortcut.Save()"
) else (
    powershell -ExecutionPolicy Bypass -Command ^
        "$WshShell = New-Object -ComObject WScript.Shell; " ^
        "$Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); " ^
        "$Shortcut.TargetPath = '%LAUNCH_SCRIPT%'; " ^
        "$Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; " ^
        "$Shortcut.Description = '个人记账软件'; " ^
        "$Shortcut.Save()"
)

if exist "%SHORTCUT%" (
    echo ✅ 快捷方式创建成功！
    echo.
    echo 📍 位置：%SHORTCUT%
    echo.
    if defined USE_ICON (
        echo 🐑 已使用自定义小羊图标！
    )
    echo.
    echo 现在您可以在桌面上双击 '记账软件' 来启动软件了！
    echo.
    echo 💡 提示：您也可以将它固定到任务栏方便使用
) else (
    echo ❌ 创建快捷方式失败
    echo.
    echo 请尝试手动创建：
    echo   1. 右键点击 '启动记账软件.bat'
    echo   2. 选择 "发送到" - "桌面快捷方式"
)

echo.
pause
