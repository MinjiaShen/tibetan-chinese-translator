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

# ── 检查 Python ──────────────────────────────────────────
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "  ❌ 未找到 Python，请先安装 Python 3.8+"
    echo ""
    echo "     macOS:    brew install python3"
    echo "     Ubuntu:   sudo apt install python3"
    echo "     CentOS:   sudo yum install python3"
    echo "     Windows:  https://www.python.org/downloads/"
    echo ""
    exit 1
fi

# 获取版本号（兼容 macOS BSD grep 和 Linux GNU grep）
PY_VER=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    echo "  ❌ Python 版本过低: $PY_VER（需要 3.8+）"
    exit 1
fi
echo "  ✅ Python $PY_VER ($PY)"

# ── 创建安装目录 ────────────────────────────────────────
mkdir -p "$INSTALL_DIR"

# ── 下载主程序 ──────────────────────────────────────────
echo "  📥 正在下载 $FILE ..."

DOWNLOAD_OK=false
if command -v curl &>/dev/null; then
    if curl -sL --fail "$RAW_URL/$FILE" -o "$INSTALL_DIR/$FILE"; then
        DOWNLOAD_OK=true
    fi
elif command -v wget &>/dev/null; then
    if wget -q "$RAW_URL/$FILE" -O "$INSTALL_DIR/$FILE"; then
        DOWNLOAD_OK=true
    fi
else
    echo "  ❌ 需要 curl 或 wget，请先安装其中一个"
    exit 1
fi

if [ "$DOWNLOAD_OK" = false ] || [ ! -s "$INSTALL_DIR/$FILE" ]; then
    echo "  ❌ 下载失败，请检查网络连接"
    rm -f "$INSTALL_DIR/$FILE"
    exit 1
fi

# ── 下载启动脚本（macOS） ──────────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
    curl -sL "$RAW_URL/start.command" -o "$INSTALL_DIR/start.command" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/start.command" 2>/dev/null || true
fi

# ── 验证文件完整性（SHA-256） ───────────────────────────
echo "  🔒 正在校验文件完整性..."
if command -v shasum &>/dev/null; then
    SHA256=$(shasum -a 256 "$INSTALL_DIR/$FILE" | cut -d' ' -f1)
elif command -v sha256sum &>/dev/null; then
    SHA256=$(sha256sum "$INSTALL_DIR/$FILE" | cut -d' ' -f1)
else
    SHA256="(sha256 工具不可用，跳过校验)"
fi
echo "  ✅ SHA-256: $SHA256"

if ! $PY -c "
import sys
sys.path.insert(0, '$INSTALL_DIR')
# 简单检查文件是否可读且包含关键类
with open('$INSTALL_DIR/$FILE', 'r') as f:
    content = f.read()
    assert 'ReusableTCPServer' in content, 'Missing ReusableTCPServer'
    assert 'find_port' in content, 'Missing find_port'
    assert 'def main' in content, 'Missing main'
" 2>/dev/null; then
    echo "  ⚠️  文件可能不完整，建议重新下载"
fi

FILE_SIZE=$(wc -c < "$INSTALL_DIR/$FILE" | tr -d ' ')
echo "  ✅ 安装完成: $INSTALL_DIR/$FILE ($FILE_SIZE bytes)"

# ── 启动提示 ──────────────────────────────────────────
echo ""
echo "  ─────────────────────────────────────────"
echo "  📋 启动方式:"
echo ""
echo "     cd \"$INSTALL_DIR\""
echo "     $PY $FILE"
echo ""
echo "  浏览器会自动打开翻译页面"
echo "  退出: Ctrl+C"
echo "  ─────────────────────────────────────────"
echo ""

# ── 询问是否立即启动 ──────────────────────────────────
# 管道模式下无法读取 stdin，自动跳过
if [ -t 0 ]; then
    read -p "  是否立即启动？[Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "  🚀 启动中..."
        cd "$INSTALL_DIR"
        exec $PY "$FILE"
    fi
else
    echo "  💡 安装完成，运行以下命令启动:"
    echo "     cd \"$INSTALL_DIR\" && $PY $FILE"
fi
