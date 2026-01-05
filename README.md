# 德州扑克在线游戏

一个基于 FastAPI + WebSocket 的德州扑克在线游戏，采用领域驱动设计（DDD）架构，支持多人实时对战。

## 功能特性

- 完整的德州扑克规则实现
- 支持 2-9 人同时游戏
- 三种下注模式：
  - 限注 (Limit)
  - 无限注 (No Limit)
  - 彩池限注 (Pot Limit)
- 专业的扑克桌 UI 设计
- WebSocket 实时游戏状态同步
- 完整的手牌评估系统
- 边池 (Side Pot) 计算
- 盲注与前注系统

## 技术栈

- **后端**: FastAPI + WebSocket
- **前端**: HTML5 + CSS3 + JavaScript
- **架构**: 领域驱动设计 (DDD)
- **异步**: Python asyncio

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd Texas
```

### 2. 安装依赖

使用 uv（推荐）：
```bash
uv sync
```

或使用 pip：
```bash
pip install fastapi uvicorn websockets jinja2 python-multipart
```

## 启动服务

```bash
python app.py
```

服务默认运行在 `http://0.0.0.0:8000`

访问浏览器打开 `http://localhost:8000` 即可开始游戏。

## 游戏流程

### 1. 登录
- 输入玩家昵称进入游戏大厅

### 2. 创建/加入房间
- **创建房间**: 设置房间名称、下注模式、盲注大小
- **加入房间**: 点击房间列表中的加入按钮

### 3. 游戏进行

游戏按照标准德州扑克规则进行：

1. **翻牌前 (Preflop)**: 每人发 2 张底牌，从大盲注下家开始下注
2. **翻牌圈 (Flop)**: 发 3 张公共牌，从庄家下家开始下注
3. **转牌圈 (Turn)**: 发第 4 张公共牌，继续下注
4. **河牌圈 (River)**: 发第 5 张公共牌，最后一轮下注
5. **摊牌 (Showdown)**: 比较手牌大小，分配底池

### 4. 玩家操作

轮到你时可以选择：
- **弃牌 (Fold)**: 放弃本局
- **过牌 (Check)**: 当前无需跟注时可以过牌
- **跟注 (Call)**: 跟上当前下注
- **加注 (Raise)**: 增加下注额
- **全押 (All-in)**: 投入所有筹码

## 下注模式说明

### 限注 (Limit)
- 每轮下注有固定的加注额
- 加注额等于大盲注

### 无限注 (No Limit)
- 可以随时全押
- 加注额无上限（除了你的筹码总量）

### 彩池限注 (Pot Limit)
- 加注额不能超过当前彩池大小
- 介于限注和无限注之间

## 牌型大小

从大到小：
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

## 项目结构

```
Texas/
├── app.py                 # FastAPI 应用入口
├── src/
│   ├── domain/            # 领域层
│   │   ├── entities.py    # 实体（Card, Player, Table）
│   │   ├── enums.py       # 枚举（Suit, Rank, Stage, BettingMode）
│   │   ├── value_objects.py  # 值对象（Pot）
│   │   └── hand_evaluator.py # 手牌评估器
│   ├── application/       # 应用层
│   │   └── game_service.py   # 游戏服务
│   ├── infrastructure/    # 基础设施层
│   │   └── websocket_manager.py  # WebSocket 连接管理
│   └── core/              # 核心层
│       └── dependencies.py    # 依赖注入
├── static/
│   ├── css/
│   │   └── style.css      # 游戏样式
│   └── js/
│       └── game.js        # 前端游戏逻辑
├── templates/
│   ├── index.html         # 登录页
│   ├── lobby.html         # 大厅页
│   └── game.html          # 游戏页
├── pyproject.toml         # 项目配置
├── rules.md               # 德州扑克规则详解
└── README.md              # 本文件
```

## API 接口

### 页面路由
- `GET /` - 登录页
- `GET /lobby` - 游戏大厅
- `GET /room/{room_id}` - 游戏房间

### API 接口
- `POST /set-player` - 设置玩家名称
- `POST /create-room` - 创建房间
- `POST /leave-room/{room_id}` - 离开房间
- `GET /api/rooms` - 获取房间列表
- `GET /api/room/{room_id}/state` - 获取房间状态

### WebSocket
- `WS /ws/{room_id}/{player_id}` - 游戏实时通信

## 常见问题

### Q: 如何让局域网内其他设备访问？
A: 服务启动后，其他设备访问 `http://<服务器IP>:8000` 即可。

### Q: 游戏中途刷新页面会怎样？
A: 重新连接后会自动恢复游戏状态。

### Q: 支持手机访问吗？
A: 支持，UI 已做响应式适配。

## 开发

### 运行开发服务器
```bash
python app.py
```
开发模式下支持热重载。

### 项目依赖
- fastapi
- uvicorn
- websockets
- jinja2
- python-multipart

## 许可证

MIT License
