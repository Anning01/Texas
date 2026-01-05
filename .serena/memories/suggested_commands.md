# 常用命令

## 依赖安装

```bash
uv sync
```

## 运行服务器

```bash
python server.py
# 或指定地址端口
python server.py --host 192.168.1.100 --port 9000
```

## 运行客户端

```bash
python client.py
# 或连接指定服务器
python client.py --host 192.168.1.100 --port 9000
```

## Windows 系统常用命令

```cmd
# 查看文件列表
dir

# 查看 IP 地址
ipconfig

# 添加防火墙规则
netsh advfirewall firewall add rule name="Texas Poker" dir=in action=allow protocol=TCP localport=8765
```

## Git 操作

```bash
git status
git add .
git commit -m "message"
git push
```
