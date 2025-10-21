#!/bin/bash
# 快速启动客户端

echo "正在启动德州扑克客户端..."
echo "默认连接到 localhost:8765"
echo ""

# 检查是否提供了服务器地址参数
if [ $# -eq 1 ]; then
    echo "连接到服务器: $1:8765"
    python3 client.py --host "$1"
elif [ $# -eq 2 ]; then
    echo "连接到服务器: $1:$2"
    python3 client.py --host "$1" --port "$2"
else
    echo "连接到本地服务器: localhost:8765"
    python3 client.py
fi
