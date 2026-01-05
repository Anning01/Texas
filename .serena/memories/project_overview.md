# Texas - 德州扑克终端游戏

## 项目概述

这是一个功能完整的德州扑克终端游戏，支持局域网多人对战。

## 技术栈

- **编程语言**: Python 3.12+
- **包管理**: uv
- **网络通信**: WebSocket (websockets 库)
- **终端UI**: Rich 库
- **并发处理**: asyncio 异步编程

## 主要依赖

- `websockets>=15.0.1` - WebSocket 通信
- `rich>=14.2.0` - 彩色终端UI
- `python-socks>=2.7.2` - SOCKS代理支持

## 项目结构

```
Texas/
├── poker_game.py      # 游戏核心逻辑(牌型评估、游戏状态)
├── server.py          # WebSocket服务器
├── client.py          # WebSocket客户端(终端UI)
├── pyproject.toml     # 项目配置
├── rules.md           # 德州扑克规则
└── README.md          # 项目文档
```

## 核心模块

### poker_game.py
- `Suit`, `Rank`, `Card` - 扑克牌基本类型
- `HandRank`, `HandValue` - 牌型等级和价值
- `Deck` - 牌组管理
- `HandEvaluator` - 手牌评估
- `BettingMode`, `GameStage` - 游戏模式和阶段
- `Player`, `Pot` - 玩家和彩池
- `GameState` - 游戏状态管理

### server.py
- `PokerServer` - WebSocket服务器，处理房间管理和游戏逻辑

### client.py
- `PokerClient` - WebSocket客户端，提供终端UI交互
