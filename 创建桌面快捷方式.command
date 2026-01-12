#!/bin/bash
# ====================================
# 在桌面创建记账软件快捷方式 (macOS)
# 带有自定义图标
# ====================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAUNCH_SCRIPT="$SCRIPT_DIR/启动记账软件.command"
ICON_PNG="$SCRIPT_DIR/src/ledger/resources/icon.png"
DESKTOP="$HOME/Desktop"
APP_NAME="记账软件.app"
APP_PATH="$DESKTOP/$APP_NAME"

echo "📁 正在创建桌面快捷方式（带自定义图标）..."
echo ""

# 检查启动脚本是否存在
if [ ! -f "$LAUNCH_SCRIPT" ]; then
    echo "❌ 错误：找不到启动脚本"
    echo "   请确保 '启动记账软件.command' 文件存在"
    read -p "按回车键退出..."
    exit 1
fi

# 检查图标文件是否存在
if [ ! -f "$ICON_PNG" ]; then
    echo "⚠️  警告：找不到图标文件，将使用默认图标"
    echo "   图标路径：$ICON_PNG"
fi

# 确保启动脚本有执行权限
chmod +x "$LAUNCH_SCRIPT"

# 如果已存在旧的快捷方式，先删除
if [ -e "$APP_PATH" ]; then
    rm -rf "$APP_PATH"
fi

# 创建 .app 目录结构
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# 创建启动器脚本
cat > "$APP_PATH/Contents/MacOS/launcher" << 'LAUNCHER'
#!/bin/bash
# 获取 .app 所在目录
APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

# 找到实际的启动脚本（通过 Info.plist 中存储的路径）
PLIST="$APP_DIR/Contents/Info.plist"
SCRIPT_PATH=$(/usr/libexec/PlistBuddy -c "Print :LaunchScript" "$PLIST" 2>/dev/null)

if [ -f "$SCRIPT_PATH" ]; then
    # 打开终端执行启动脚本
    osascript -e "tell application \"Terminal\"
        activate
        do script \"'$SCRIPT_PATH'\"
    end tell"
else
    osascript -e 'display alert "错误" message "找不到启动脚本，请重新创建快捷方式。"'
fi
LAUNCHER

chmod +x "$APP_PATH/Contents/MacOS/launcher"

# 转换 PNG 到 ICNS（如果图标存在）
if [ -f "$ICON_PNG" ]; then
    echo "🎨 正在转换图标格式..."
    
    # 创建临时 iconset 目录
    ICONSET="$APP_PATH/Contents/Resources/icon.iconset"
    mkdir -p "$ICONSET"
    
    # 使用 sips 生成不同尺寸的图标
    sips -z 16 16     "$ICON_PNG" --out "$ICONSET/icon_16x16.png" > /dev/null 2>&1
    sips -z 32 32     "$ICON_PNG" --out "$ICONSET/icon_16x16@2x.png" > /dev/null 2>&1
    sips -z 32 32     "$ICON_PNG" --out "$ICONSET/icon_32x32.png" > /dev/null 2>&1
    sips -z 64 64     "$ICON_PNG" --out "$ICONSET/icon_32x32@2x.png" > /dev/null 2>&1
    sips -z 128 128   "$ICON_PNG" --out "$ICONSET/icon_128x128.png" > /dev/null 2>&1
    sips -z 256 256   "$ICON_PNG" --out "$ICONSET/icon_128x128@2x.png" > /dev/null 2>&1
    sips -z 256 256   "$ICON_PNG" --out "$ICONSET/icon_256x256.png" > /dev/null 2>&1
    sips -z 512 512   "$ICON_PNG" --out "$ICONSET/icon_256x256@2x.png" > /dev/null 2>&1
    sips -z 512 512   "$ICON_PNG" --out "$ICONSET/icon_512x512.png" > /dev/null 2>&1
    sips -z 1024 1024 "$ICON_PNG" --out "$ICONSET/icon_512x512@2x.png" > /dev/null 2>&1
    
    # 转换为 icns
    iconutil -c icns "$ICONSET" -o "$APP_PATH/Contents/Resources/icon.icns" 2>/dev/null
    
    # 清理临时文件
    rm -rf "$ICONSET"
    
    ICON_NAME="icon"
else
    ICON_NAME="AppIcon"
fi

# 创建 Info.plist
cat > "$APP_PATH/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>$ICON_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>com.ledger.app</string>
    <key>CFBundleName</key>
    <string>记账软件</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LaunchScript</key>
    <string>$LAUNCH_SCRIPT</string>
</dict>
</plist>
PLIST

# 刷新图标缓存
touch "$APP_PATH"

if [ -d "$APP_PATH" ]; then
    echo ""
    echo "✅ 快捷方式创建成功！"
    echo ""
    echo "📍 位置：$APP_PATH"
    echo ""
    echo "🐑 已使用自定义小羊图标！"
    echo ""
    echo "现在您可以在桌面上双击 '记账软件' 来启动软件了！"
    echo ""
    echo "💡 提示：您也可以将它拖到 Dock 栏上方便使用"
else
    echo "❌ 创建快捷方式失败"
    echo "   请尝试手动创建："
    echo "   1. 在 Finder 中找到 '启动记账软件.command'"
    echo "   2. 按住 Option+Command 拖到桌面"
fi

echo ""
read -p "按回车键关闭..."
