#!/bin/bash
# 快速启动服务器

echo "正在启动德州扑克服务器..."
echo "服务器将监听 0.0.0.0:8765"
echo "局域网内其他设备可以通过你的IP地址连接"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

python3 server.py
