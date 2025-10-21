# 德州扑克终端游戏

一个功能完整的德州扑克终端游戏,支持局域网多人对战,使用WebSocket实现实时通信,使用Rich库提供彩色终端界面。

## 功能特性

- ✅ 完整的德州扑克规则实现
- ✅ 支持2-9人同时游戏
- ✅ 三种游戏模式:
  - 限注 (Limit)
  - 无限注 (No Limit)
  - 彩池限注 (Pot Limit)
- ✅ 房主控制游戏开始和结束
- ✅ 精美的彩色终端UI
- ✅ 实时游戏状态同步
- ✅ 完整的手牌评估系统
- ✅ 边池(Side Pot)计算
- ✅ 盲注系统

## 安装

### 1. 克隆或下载项目

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

依赖包:
- `websockets` - WebSocket通信
- `rich` - 彩色终端UI

## 使用方法

### 启动服务器

在一台电脑上运行服务器:

```bash
python server.py
```

默认监听 `0.0.0.0:8765`

自定义地址和端口:

```bash
python server.py --host 192.168.1.100 --port 9000
```

### 启动客户端

在同一台或其他电脑上运行客户端:

```bash
python client.py
```

连接到指定服务器:

```bash
python client.py --host 192.168.1.100 --port 9000
```

## 游戏流程

### 1. 创建/加入房间

启动客户端后选择:
- **创建房间**: 作为房主创建新房间,可以选择游戏模式
- **加入房间**: 输入房间ID加入已有房间
- **查看房间列表**: 查看当前所有可用房间

### 2. 等待玩家

- 至少需要2名玩家才能开始游戏
- 房主可以在等待界面选择开始游戏

### 3. 游戏进行

游戏按照标准德州扑克规则进行:

1. **翻牌前 (Preflop)**: 每人发2张底牌,从大盲注下家开始下注
2. **翻牌圈 (Flop)**: 发3张公共牌,从庄家下家开始下注
3. **转牌圈 (Turn)**: 发第4张公共牌,继续下注
4. **河牌圈 (River)**: 发第5张公共牌,最后一轮下注
5. **摊牌 (Showdown)**: 比较手牌大小,分配底池

### 4. 玩家操作

轮到你时可以选择:
- **弃牌 (Fold)**: 放弃本局
- **过牌 (Check)**: 当前无需跟注时可以过牌
- **跟注 (Call)**: 跟上当前下注
- **加注 (Raise)**: 增加下注额
- **全押 (All-in)**: 投入所有筹码

## 游戏模式说明

### 限注 (Limit)
- 每轮下注有固定的加注额
- 加注额等于大盲注

### 无限注 (No Limit)
- 可以随时全押
- 加注额无上限(除了你的筹码总量)

### 彩池限注 (Pot Limit)
- 加注额不能超过当前彩池大小
- 介于限注和无限注之间

## 牌型大小

从大到小:
1. 皇家同花顺 (Royal Flush)
2. 同花顺 (Straight Flush)
3. 四条 (Four of a Kind)
4. 葫芦 (Full House)
5. 同花 (Flush)
6. 顺子 (Straight)
7. 三条 (Three of a Kind)
8. 两对 (Two Pair)
9. 一对 (Pair)
10. 高牌 (High Card)

## 界面说明

游戏界面分为三个区域:

### 顶部 - 房间信息
- 房间ID
- 游戏模式
- 当前阶段
- 底池大小

### 中间 - 游戏桌
- 公共牌显示(红色♥♦,黑色♣♠)
- 玩家列表:
  - 🎯 D: 庄家位置
  - SB: 小盲注
  - BB: 大盲注
  - 👤: 你自己
- 每个玩家的筹码和下注情况
- 手牌(只能看到自己的)

### 底部 - 操作区
- 当轮到你时显示可用操作
- 其他时间显示等待提示

## 局域网设置

### 查找服务器IP地址

**Windows:**
```cmd
ipconfig
```
查看 IPv4 地址

**Mac/Linux:**
```bash
ifconfig
# 或
ip addr show
```

### 防火墙设置

确保服务器端口(默认8765)在防火墙中开放。

**Windows:**
```cmd
netsh advfirewall firewall add rule name="Texas Poker" dir=in action=allow protocol=TCP localport=8765
```

**Linux (ufw):**
```bash
sudo ufw allow 8765/tcp
```

**Mac:**
系统偏好设置 > 安全性与隐私 > 防火墙 > 防火墙选项 > 添加Python

## 项目结构

```
Texas/
├── poker_game.py      # 游戏核心逻辑(牌型评估、游戏状态)
├── server.py          # WebSocket服务器
├── client.py          # WebSocket客户端(终端UI)
├── requirements.txt   # 依赖包
├── rules.md          # 德州扑克规则
└── README.md         # 本文件
```

## 技术实现

- **游戏引擎**: 纯Python实现,包含完整的德州扑克规则
- **网络通信**: WebSocket (websockets库)
- **终端UI**: Rich库提供彩色终端、表格、面板等组件
- **并发处理**: asyncio异步编程

## 常见问题

### Q: 客户端连接不上服务器?
A: 检查:
1. 服务器是否正在运行
2. IP地址和端口是否正确
3. 防火墙是否放行
4. 是否在同一局域网

### Q: 游戏界面显示乱码?
A: 确保终端支持UTF-8编码,建议使用:
- Windows: Windows Terminal
- Mac: Terminal.app 或 iTerm2
- Linux: gnome-terminal 或 konsole

### Q: 可以在互联网上玩吗?
A: 可以,但需要:
1. 服务器有公网IP或使用端口转发
2. 客户端使用公网IP连接
3. 注意安全性,建议使用VPN

### Q: 如何查看手牌牌型?
A: 摊牌时会自动显示赢家的牌型名称

## 开发者

这是一个开源项目,欢迎贡献代码和提出建议!

## 许可证

MIT License

## 更新日志

### v1.0.0 (2024)
- 初始版本
- 实现完整的德州扑克规则
- 支持三种游戏模式
- 彩色终端UI
- 局域网多人对战
