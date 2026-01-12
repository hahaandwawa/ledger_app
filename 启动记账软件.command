#!/bin/bash
# ====================================
# 个人记账软件 - macOS 启动脚本
# 双击此文件即可启动软件
# ====================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 切换到软件目录
cd "$SCRIPT_DIR"

echo "🚀 正在启动记账软件..."
echo ""

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "⚠️  首次运行，正在安装必要组件..."
    echo "   这可能需要几分钟，请耐心等待..."
    echo ""
    
    # 创建虚拟环境
    python3 -m venv venv
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ 错误：无法创建虚拟环境"
        echo ""
        echo "请确保已安装 Python 3："
        echo "  1. 访问 https://www.python.org/downloads/"
        echo "  2. 下载并安装 Python 3"
        echo "  3. 重新运行此脚本"
        echo ""
        read -p "按回车键退出..."
        exit 1
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ 错误：安装依赖失败"
        echo "请检查网络连接后重试"
        echo ""
        read -p "按回车键退出..."
        exit 1
    fi
    
    echo ""
    echo "✅ 安装完成！"
    echo ""
fi

# 激活虚拟环境
source venv/bin/activate

# 启动软件
echo "💰 记账软件启动中..."
python src/ledger/main.py

# 如果软件异常退出，显示提示
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  软件已退出"
    read -p "按回车键关闭此窗口..."
fi

