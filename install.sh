#!/bin/bash
# 🏔️ 藏语→中文 实时翻译工具 — 一键安装脚本
# 用法: curl -sL https://raw.githubusercontent.com/MinjiaShen/tibetan-chinese-translator/main/install.sh | bash

set -e

REPO="MinjiaShen/tibetan-chinese-translator"
RAW_URL="https://raw.githubusercontent.com/$REPO/main"
INSTALL_DIR="$HOME/tibetan-translator"
FILE="tibetan-translator.py"

echo ""
echo "  🏔️  藏语→中文 实时翻译工具 — 安装中..."
echo ""

# 检查 Python
if command -v python3 &>/dev/null; then
    PY=python3
    PY_VER=$($PY --version 2>&1 | grep -oP '\d+\.\d+')
elif command -v python &>/dev/null; then
    PY=python
    PY_VER=$($PY --version 2>&1 | grep -oP '\d+\.\d+')
else
    echo "  ❌ 未找到 Python，请先安装 Python 3.8+"
    echo "     macOS:  brew install python3"
    echo "     Ubuntu: sudo apt install python3"
    echo "     Windows: https://www.python.org/downloads/"
    exit 1
fi

# 检查 Python 版本 >= 3.8
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
    echo "  ❌ Python 版本过低: $PY_VER（需要 3.8+）"
    exit 1
fi
echo "  ✅ Python $PY_VER ($PY)"

# 创建安装目录
mkdir -p "$INSTALL_DIR"

# 下载主程序
echo "  📥 下载 $FILE ..."
if command -v curl &>/dev/null; then
    curl -sL "$RAW_URL/$FILE" -o "$INSTALL_DIR/$FILE"
elif command -v wget &>/dev/null; then
    wget -q "$RAW_URL/$FILE" -O "$INSTALL_DIR/$FILE"
else
    echo "  ❌ 需要 curl 或 wget"
    exit 1
fi

# 下载启动脚本
if [[ "$OSTYPE" == "darwin"* ]]; then
    curl -sL "$RAW_URL/start.command" -o "$INSTALL_DIR/start.command" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/start.command" 2>/dev/null || true
fi

echo "  ✅ 安装完成: $INSTALL_DIR/$FILE"
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║  启动方式:                            ║"
echo "  ║                                      ║"
echo "  ║  cd $INSTALL_DIR"
echo "  ║  $PY $FILE              ║"
echo "  ║                                      ║"
echo "  ║  浏览器会自动打开翻译页面              ║"
echo "  ║  退出: Ctrl+C                         ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# 询问是否立即启动
read -p "  是否立即启动？[Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "  🚀 启动中..."
    cd "$INSTALL_DIR"
    exec $PY "$FILE"
fi
