"""FastAPI 德州扑克在线游戏"""
import uuid
import asyncio
import time
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from urllib.parse import quote, unquote

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from poker_game import GameState, BettingMode, GameStage, Card, HandEvaluator


# ============ 数据类 ============

@dataclass
class ChatMessage:
    """聊天消息"""
    player_name: str
    content: str
    timestamp: float = field(default_factory=time.time)
    msg_type: str = "chat"  # chat, system, action


@dataclass
class GameAction:
    """游戏操作记录"""
    player_name: str
    action: str
    amount: int = 0
    timestamp: float = field(default_factory=time.time)


# ============ 游戏管理器 ============

class ConnectionManager:
    """WebSocket 连接管理"""
    
    def __init__(self):
        # room_id -> {player_id -> websocket}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}
    
    async def connect(self, room_id: str, player_id: str, websocket: WebSocket):
        """添加连接"""
        await websocket.accept()
        if room_id not in self.connections:
            self.connections[room_id] = {}
        self.connections[room_id][player_id] = websocket
    
    def disconnect(self, room_id: str, player_id: str):
        """移除连接"""
        if room_id in self.connections:
            self.connections[room_id].pop(player_id, None)
            if not self.connections[room_id]:
                del self.connections[room_id]
    
    async def broadcast_to_room(self, room_id: str, message: dict):
        """广播消息到房间所有玩家"""
        if room_id in self.connections:
            for websocket in self.connections[room_id].values():
                try:
                    await websocket.send_json(message)
                except:
                    pass
    
    async def send_to_player(self, room_id: str, player_id: str, message: dict):
        """发送消息给指定玩家"""
        if room_id in self.connections and player_id in self.connections[room_id]:
            try:
                await self.connections[room_id][player_id].send_json(message)
            except:
                pass


class GameManager:
    """游戏房间管理"""
    
    TURN_TIMEOUT = 30  # 每回合30秒超时
    
    def __init__(self):
        self.rooms: Dict[str, GameState] = {}
        self.room_names: Dict[str, str] = {}  # room_id -> room_name
        self.connection_manager = ConnectionManager()
        self.chat_history: Dict[str, List[ChatMessage]] = {}  # room_id -> messages
        self.action_history: Dict[str, List[GameAction]] = {}  # room_id -> actions
        self.turn_timers: Dict[str, asyncio.Task] = {}  # room_id -> timer task
        self.turn_start_time: Dict[str, float] = {}  # room_id -> start timestamp
    
    def create_room(self, room_name: str, mode: BettingMode = BettingMode.NO_LIMIT,
                    small_blind: int = 10, big_blind: int = 20, ante: int = 0) -> str:
        """创建房间"""
        room_id = str(uuid.uuid4())[:8].upper()
        game = GameState(betting_mode=mode)
        game.small_blind = small_blind
        game.big_blind = big_blind
        game.ante = ante
        game.min_raise = big_blind
        self.rooms[room_id] = game
        self.room_names[room_id] = room_name
        self.chat_history[room_id] = []
        self.action_history[room_id] = []
        return room_id
    
    def get_room(self, room_id: str) -> Optional[GameState]:
        """获取房间"""
        return self.rooms.get(room_id)
    
    def get_room_list(self) -> List[dict]:
        """获取房间列表"""
        result = []
        for room_id, game in self.rooms.items():
            result.append({
                "id": room_id,
                "name": self.room_names.get(room_id, "未命名房间"),
                "player_count": len(game.players),
                "stage": game.stage.value,
                "mode": game.betting_mode.value
            })
        return result
    
    MAX_PLAYERS = 10  # 标准德州扑克最多10人
    
    def join_room(self, room_id: str, player_id: str, player_name: str) -> bool:
        """加入房间"""
        game = self.get_room(room_id)
        if not game:
            return False
        if len(game.players) >= self.MAX_PLAYERS:
            return False
        # 检查是否已在房间
        for p in game.players:
            if p.id == player_id:
                return True
        game.add_player(player_id, player_name)
        return True
    
    def leave_room(self, room_id: str, player_id: str):
        """离开房间"""
        game = self.get_room(room_id)
        if game:
            game.remove_player(player_id)
            # 如果房间没人了，删除房间
            if len(game.players) == 0:
                del self.rooms[room_id]
                self.room_names.pop(room_id, None)
    
    def delete_room(self, room_id: str):
        """删除房间"""
        self.rooms.pop(room_id, None)
        self.room_names.pop(room_id, None)
        self.chat_history.pop(room_id, None)
        self.action_history.pop(room_id, None)
        self._cancel_timer(room_id)
    
    def _cancel_timer(self, room_id: str):
        """取消计时器"""
        if room_id in self.turn_timers:
            self.turn_timers[room_id].cancel()
            del self.turn_timers[room_id]
        self.turn_start_time.pop(room_id, None)
    
    async def _start_turn_timer(self, room_id: str):
        """启动回合计时器"""
        self._cancel_timer(room_id)
        self.turn_start_time[room_id] = time.time()
        
        async def timeout_handler():
            await asyncio.sleep(self.TURN_TIMEOUT)
            # 超时自动弃牌
            game = self.get_room(room_id)
            if game and game.stage not in [GameStage.WAITING, GameStage.SHOWDOWN]:
                current_player = None
                for p in game.players:
                    if p.position == game.current_player_index:
                        current_player = p
                        break
                if current_player and not current_player.folded:
                    await self.handle_action(room_id, current_player.id, {"action": "fold"})
                    # 广播超时消息
                    await self.broadcast_chat(room_id, ChatMessage(
                        player_name="系统",
                        content=f"{current_player.name} 超时自动弃牌",
                        msg_type="system"
                    ))
        
        self.turn_timers[room_id] = asyncio.create_task(timeout_handler())
    
    def get_remaining_time(self, room_id: str) -> int:
        """获取剩余时间"""
        if room_id not in self.turn_start_time:
            return self.TURN_TIMEOUT
        elapsed = time.time() - self.turn_start_time[room_id]
        return max(0, int(self.TURN_TIMEOUT - elapsed))
    
    def add_action(self, room_id: str, player_name: str, action: str, amount: int = 0):
        """添加操作记录"""
        if room_id not in self.action_history:
            self.action_history[room_id] = []
        self.action_history[room_id].append(GameAction(
            player_name=player_name,
            action=action,
            amount=amount
        ))
        # 只保留最近50条
        if len(self.action_history[room_id]) > 50:
            self.action_history[room_id] = self.action_history[room_id][-50:]
    
    async def broadcast_chat(self, room_id: str, message: ChatMessage):
        """广播聊天消息"""
        if room_id not in self.chat_history:
            self.chat_history[room_id] = []
        self.chat_history[room_id].append(message)
        # 只保留最近100条
        if len(self.chat_history[room_id]) > 100:
            self.chat_history[room_id] = self.chat_history[room_id][-100:]
        
        await self.connection_manager.broadcast_to_room(room_id, {
            "type": "chat",
            "data": {
                "player_name": message.player_name,
                "content": message.content,
                "msg_type": message.msg_type,
                "timestamp": message.timestamp
            }
        })
    
    def get_game_state_for_player(self, room_id: str, player_id: str) -> Optional[dict]:
        """获取玩家视角的游戏状态"""
        game = self.get_room(room_id)
        if not game:
            return None
        
        # 构建玩家列表（隐藏其他玩家的手牌）
        players_data = []
        for p in game.players:
            player_data = {
                "id": p.id,
                "name": p.name,
                "chips": p.chips,
                "current_bet": p.current_bet,
                "total_bet": p.total_bet,
                "folded": p.folded,
                "all_in": p.all_in,
                "position": p.position,
                "is_dealer": p.position == game.dealer_position,
                "is_current": p.position == game.current_player_index,
                "is_self": p.id == player_id,
            }
            # 只有自己能看到自己的手牌，或者摊牌阶段未弃牌玩家可见
            if p.id == player_id:
                player_data["hand"] = [self._card_to_dict(c) for c in p.hand]
            elif game.stage == GameStage.SHOWDOWN and not p.folded:
                # 摊牌阶段，未弃牌的玩家亮牌
                player_data["hand"] = [self._card_to_dict(c) for c in p.hand]
            else:
                player_data["hand"] = [{"hidden": True}, {"hidden": True}] if p.hand else []
            players_data.append(player_data)
        
        # 当前玩家
        current_player = None
        for p in game.players:
            if p.id == player_id:
                current_player = p
                break
        
        # 获取小盲注和大盲注位置
        num_players = len(game.players)
        if num_players >= 2:
            if num_players == 2:
                sb_position = game.dealer_position
                bb_position = (game.dealer_position + 1) % num_players
            else:
                sb_position = (game.dealer_position + 1) % num_players
                bb_position = (game.dealer_position + 2) % num_players
        else:
            sb_position = -1
            bb_position = -1
        
        # 标记玩家位置
        for p_data in players_data:
            p_data["is_sb"] = p_data["position"] == sb_position
            p_data["is_bb"] = p_data["position"] == bb_position
        
        # 判断当前轮是否已有人下注（用于区分Bet和Raise）
        # 翻牌前盲注算作下注，翻牌后需要看current_bet是否>0
        has_bet_this_round = game.current_bet > 0
        
        # 计算下注/加注金额范围
        if current_player:
            to_call = game.current_bet - current_player.current_bet
            # 根据下注模式计算最小和最大加注额
            min_raise_amount = game.get_min_raise()
            max_raise_amount = game.get_max_raise(current_player)
            # 限注模式下，最小=最大
            if game.betting_mode == BettingMode.LIMIT:
                min_raise_amount = max_raise_amount
        else:
            to_call = 0
            min_raise_amount = game.get_min_raise()
            max_raise_amount = 0
        
        return {
            "room_id": room_id,
            "room_name": self.room_names.get(room_id, ""),
            "stage": game.stage.value,
            "betting_mode": game.betting_mode.value,
            "community_cards": [self._card_to_dict(c) for c in game.community_cards],
            "main_pot": game.main_pot,
            "current_bet": game.current_bet,
            "min_raise": min_raise_amount,
            "max_raise": max_raise_amount,  # 根据下注模式计算的最大加注额
            "has_bet_this_round": has_bet_this_round,  # 当前轮是否已有下注
            "to_call": to_call,  # 需要跟注的金额
            "raise_count": game.raise_count,  # 当前轮加注次数
            "max_raises": game.max_raises,  # 限注模式最大加注次数
            "dealer_position": game.dealer_position,
            "current_player_index": game.current_player_index,
            "players": players_data,
            "is_my_turn": current_player and game.current_player_index == current_player.position and game.stage not in [GameStage.WAITING, GameStage.SHOWDOWN],
            "is_room_owner": game.room_owner == player_id,
            "can_start": len(game.players) >= 2 and game.stage == GameStage.WAITING,
            "remaining_time": self.get_remaining_time(room_id),
            "small_blind": game.small_blind,
            "big_blind": game.big_blind,
            "ante": game.ante,
            "action_history": [
                {"player": a.player_name, "action": a.action, "amount": a.amount}
                for a in (self.action_history.get(room_id, []))[-10:]
            ],
            "showdown_order": [p.name for p in game.get_showdown_order()] if game.stage == GameStage.SHOWDOWN else [],
        }
    
    def _card_to_dict(self, card: Card) -> dict:
        """卡牌转字典"""
        return {
            "suit": card.suit.value,
            "rank": card.rank.display,
            "color": "red" if card.suit.value in ["♥", "♦"] else "black"
        }
    
    async def handle_action(self, room_id: str, player_id: str, action: dict):
        """处理玩家操作"""
        game = self.get_room(room_id)
        if not game:
            return
        
        action_type = action.get("action")
        
        if action_type == "chat":
            # 处理聊天消息
            content = action.get("content", "").strip()
            if content:
                player_name = "未知"
                for p in game.players:
                    if p.id == player_id:
                        player_name = p.name
                        break
                await self.broadcast_chat(room_id, ChatMessage(
                    player_name=player_name,
                    content=content[:200],  # 限制长度
                    msg_type="chat"
                ))
            return
        
        if action_type == "start_game":
            if game.room_owner == player_id and len(game.players) >= 2:
                game.start_new_hand()
                self.action_history[room_id] = []  # 清空操作记录
                await self._start_turn_timer(room_id)
                await self.broadcast_chat(room_id, ChatMessage(
                    player_name="系统",
                    content="新一局开始！",
                    msg_type="system"
                ))
                await self.broadcast_game_state(room_id)
        
        elif action_type in ["fold", "check", "call", "bet", "raise", "all_in"]:
            # 找到当前玩家
            current_player = None
            for p in game.players:
                if p.position == game.current_player_index:
                    current_player = p
                    break
            
            if not current_player or current_player.id != player_id:
                return  # 不是你的回合
            
            action_text = ""
            action_amount = 0
            
            if action_type == "fold":
                current_player.folded = True
                current_player.has_acted = True
                action_text = "弃牌"
            
            elif action_type == "check":
                if game.current_bet > current_player.current_bet:
                    return  # 不能过牌
                current_player.has_acted = True
                action_text = "过牌"
            
            elif action_type == "call":
                call_amount = game.current_bet - current_player.current_bet
                call_amount = min(call_amount, current_player.chips)
                current_player.chips -= call_amount
                current_player.current_bet += call_amount
                current_player.total_bet += call_amount
                game.main_pot += call_amount
                current_player.has_acted = True
                if current_player.chips == 0:
                    current_player.all_in = True
                action_text = "跟注"
                action_amount = call_amount
            
            elif action_type == "bet":
                # 下注（翻牌后首次下注）
                min_bet = game.get_min_raise()
                max_bet = game.get_max_raise(current_player)
                
                # 如果不能下注（限注模式达到最大次数），忽略此操作
                if max_bet <= 0:
                    return
                
                bet_amount = action.get("amount", min_bet)
                
                # 限制在允许范围内
                if bet_amount < min_bet:
                    bet_amount = min_bet
                if bet_amount > max_bet:
                    bet_amount = max_bet
                if bet_amount > current_player.chips:
                    bet_amount = current_player.chips
                    current_player.all_in = True
                    
                current_player.chips -= bet_amount
                current_player.current_bet = bet_amount
                current_player.total_bet += bet_amount
                game.main_pot += bet_amount
                game.current_bet = bet_amount
                game.min_raise = bet_amount  # 下一次加注至少要加这么多
                game.last_raiser_index = current_player.position
                game.raise_count += 1  # 下注也算一次（限注模式）
                current_player.has_acted = True
                # 有人下注，其他人需要行动
                for p in game.players:
                    if p.id != current_player.id and not p.folded and not p.all_in:
                        p.has_acted = False
                action_text = "下注"
                action_amount = bet_amount
            
            elif action_type == "raise":
                # 加注（在已有下注基础上加注）
                min_raise = game.get_min_raise()
                max_raise = game.get_max_raise(current_player)
                
                # 如果不能加注（限注模式达到最大次数），忽略此操作
                if max_raise <= 0:
                    return
                
                raise_amount = action.get("amount", min_raise)
                
                # 限制在允许范围内
                if raise_amount < min_raise:
                    raise_amount = min_raise
                if raise_amount > max_raise:
                    raise_amount = max_raise
                    
                total_bet = game.current_bet + raise_amount
                need_chips = total_bet - current_player.current_bet
                
                if need_chips > current_player.chips:
                    need_chips = current_player.chips
                    current_player.all_in = True
                current_player.chips -= need_chips
                current_player.current_bet += need_chips
                current_player.total_bet += need_chips
                game.main_pot += need_chips
                game.current_bet = current_player.current_bet
                game.min_raise = raise_amount  # 记录加注增量，下次加注至少要加这么多
                game.last_raiser_index = current_player.position
                game.raise_count += 1  # 增加加注次数
                current_player.has_acted = True
                
                # 加注后，其他所有人需要重新行动
                for p in game.players:
                    if p.id != current_player.id and not p.folded and not p.all_in:
                        p.has_acted = False
                action_text = "加注"
                action_amount = need_chips
            
            elif action_type == "all_in":
                all_in_amount = current_player.chips
                current_player.chips = 0
                current_player.current_bet += all_in_amount
                current_player.total_bet += all_in_amount
                game.main_pot += all_in_amount
                current_player.all_in = True
                current_player.has_acted = True
                if current_player.current_bet > game.current_bet:
                    game.current_bet = current_player.current_bet
                    game.last_raiser_index = current_player.position
                    # 全押金额超过当前下注，其他人需要重新行动
                    for p in game.players:
                        if p.id != current_player.id and not p.folded and not p.all_in:
                            p.has_acted = False
                action_text = "全押"
                action_amount = all_in_amount
            
            # 记录操作
            if action_text:
                self.add_action(room_id, current_player.name, action_text, action_amount)
            
            # 移动到下一个玩家
            next_idx = game.get_next_active_player_index(game.current_player_index)
            
            # 检查是否只剩一个玩家未弃牌
            active_players = game.get_active_players()
            if len(active_players) == 1:
                # 直接结束，唯一剩余玩家获胜
                self._cancel_timer(room_id)
                game.stage = GameStage.SHOWDOWN
                winners = game.determine_winners()
                await self.broadcast_game_state(room_id, winners=winners)
                await self.broadcast_chat(room_id, ChatMessage(
                    player_name="系统",
                    content=f"🏆 {winners[0][0].name} 赢得 {winners[0][1]} 筹码！",
                    msg_type="system"
                ))
                game.end_hand()
                return
            
            # 【重要】先检查下注轮是否完成
            if game.is_betting_round_complete():
                # 下注轮完成，检查是否需要进入下一阶段
                
                # 检查是否所有人都全押或弃牌（只剩0或1个可以行动的玩家）
                players_can_act = [p for p in game.players if not p.folded and not p.all_in]
                if len(players_can_act) <= 1:
                    # 所有人都全押了，直接发完所有公共牌并摊牌
                    self._cancel_timer(room_id)
                    while game.stage != GameStage.RIVER and game.stage != GameStage.SHOWDOWN:
                        game.advance_stage()
                        stage_names = {
                            GameStage.FLOP: "翻牌",
                            GameStage.TURN: "转牌", 
                            GameStage.RIVER: "河牌"
                        }
                        if game.stage in stage_names:
                            await self.broadcast_chat(room_id, ChatMessage(
                                player_name="系统",
                                content=f"进入{stage_names.get(game.stage, '')}阶段",
                                msg_type="system"
                            ))
                            await self.broadcast_game_state(room_id)
                            await asyncio.sleep(1)  # 延迟显示每个阶段
                    
                    game.stage = GameStage.SHOWDOWN
                    winners = game.determine_winners()
                    await self.broadcast_game_state(room_id, winners=winners)
                    for w in winners:
                        hand_name = HandEvaluator.get_hand_name(w[2])
                        await self.broadcast_chat(room_id, ChatMessage(
                            player_name="系统",
                            content=f"🏆 {w[0].name} 以 {hand_name} 赢得 {w[1]} 筹码！",
                            msg_type="system"
                        ))
                    game.end_hand()
                    return
                
                # 正常进入下一阶段
                if game.stage == GameStage.RIVER:
                    self._cancel_timer(room_id)
                    game.stage = GameStage.SHOWDOWN
                    winners = game.determine_winners()
                    await self.broadcast_game_state(room_id, winners=winners)
                    # 广播赢家信息
                    for w in winners:
                        hand_name = HandEvaluator.get_hand_name(w[2])
                        await self.broadcast_chat(room_id, ChatMessage(
                            player_name="系统",
                            content=f"🏆 {w[0].name} 以 {hand_name} 赢得 {w[1]} 筹码！",
                            msg_type="system"
                        ))
                    game.end_hand()
                    return
                else:
                    game.advance_stage()
                    stage_names = {
                        GameStage.FLOP: "翻牌",
                        GameStage.TURN: "转牌", 
                        GameStage.RIVER: "河牌"
                    }
                    await self.broadcast_chat(room_id, ChatMessage(
                        player_name="系统",
                        content=f"进入{stage_names.get(game.stage, '')}阶段",
                        msg_type="system"
                    ))
            else:
                # 下注轮未完成，移动到下一个玩家
                game.current_player_index = next_idx
            
            # 重启计时器
            await self._start_turn_timer(room_id)
            await self.broadcast_game_state(room_id)
    
    async def broadcast_game_state(self, room_id: str, winners: list = None):
        """广播游戏状态给房间所有玩家"""
        game = self.get_room(room_id)
        if not game:
            return
        
        for player in game.players:
            state = self.get_game_state_for_player(room_id, player.id)
            if state:
                if winners:
                    state["winners"] = [
                        {"name": w[0].name, "amount": w[1], "hand_name": w[2].rank.name}
                        for w in winners
                    ]
                await self.connection_manager.send_to_player(room_id, player.id, {
                    "type": "game_state",
                    "data": state
                })


# ============ FastAPI 应用 ============

game_manager = GameManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    yield


app = FastAPI(title="德州扑克", lifespan=lifespan)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ============ 页面路由 ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, player_id: Optional[str] = Cookie(None)):
    """首页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "player_id": player_id
    })


@app.post("/set-player")
async def set_player(player_name: str = Form(...)):
    """设置玩家名称"""
    player_id = str(uuid.uuid4())
    # URL编码支持中文名
    encoded_name = quote(player_name, safe='')
    response = RedirectResponse(url="/lobby", status_code=303)
    response.set_cookie(key="player_id", value=player_id, max_age=86400)
    response.set_cookie(key="player_name", value=encoded_name, max_age=86400)
    return response


@app.get("/lobby", response_class=HTMLResponse)
async def lobby(
    request: Request,
    player_id: Optional[str] = Cookie(None),
    player_name: Optional[str] = Cookie(None)
):
    """大厅页面"""
    if not player_id or not player_name:
        return RedirectResponse(url="/")
    
    # 解码中文名
    decoded_name = unquote(player_name)
    rooms = game_manager.get_room_list()
    return templates.TemplateResponse("lobby.html", {
        "request": request,
        "player_id": player_id,
        "player_name": decoded_name,
        "rooms": rooms
    })


@app.post("/create-room")
async def create_room(
    room_name: str = Form(...),
    betting_mode: str = Form("no_limit"),
    small_blind: int = Form(10),
    big_blind: int = Form(20),
    ante: int = Form(0),
    player_id: Optional[str] = Cookie(None),
    player_name: Optional[str] = Cookie(None)
):
    """创建房间"""
    if not player_id or not player_name:
        return RedirectResponse(url="/")
    
    # 解码中文名
    decoded_name = unquote(player_name)
    
    mode_map = {
        "limit": BettingMode.LIMIT,
        "no_limit": BettingMode.NO_LIMIT,
        "pot_limit": BettingMode.POT_LIMIT
    }
    mode = mode_map.get(betting_mode, BettingMode.NO_LIMIT)
    
    # 验证盲注参数
    small_blind = max(1, small_blind)
    big_blind = max(small_blind * 2, big_blind)
    ante = max(0, ante)
    
    room_id = game_manager.create_room(room_name, mode, small_blind, big_blind, ante)
    game_manager.join_room(room_id, player_id, decoded_name)
    
    return RedirectResponse(url=f"/room/{room_id}", status_code=303)


@app.get("/room/{room_id}", response_class=HTMLResponse)
async def game_room(
    request: Request,
    room_id: str,
    player_id: Optional[str] = Cookie(None),
    player_name: Optional[str] = Cookie(None)
):
    """游戏房间页面"""
    if not player_id or not player_name:
        return RedirectResponse(url="/")
    
    # 解码中文名
    decoded_name = unquote(player_name)
    
    game = game_manager.get_room(room_id)
    if not game:
        return RedirectResponse(url="/lobby")
    
    # 加入房间
    game_manager.join_room(room_id, player_id, decoded_name)
    
    return templates.TemplateResponse("game.html", {
        "request": request,
        "room_id": room_id,
        "player_id": player_id,
        "player_name": decoded_name,
        "room_name": game_manager.room_names.get(room_id, "")
    })


@app.post("/leave-room/{room_id}")
async def leave_room(
    room_id: str,
    player_id: Optional[str] = Cookie(None)
):
    """离开房间"""
    if player_id:
        game_manager.leave_room(room_id, player_id)
    return RedirectResponse(url="/lobby", status_code=303)


# ============ WebSocket ============

@app.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    """WebSocket 连接"""
    game = game_manager.get_room(room_id)
    if not game:
        await websocket.close()
        return
    
    await game_manager.connection_manager.connect(room_id, player_id, websocket)
    
    try:
        # 发送初始状态
        state = game_manager.get_game_state_for_player(room_id, player_id)
        if state:
            await websocket.send_json({"type": "game_state", "data": state})
        
        # 广播玩家加入
        await game_manager.broadcast_game_state(room_id)
        
        # 接收消息
        while True:
            data = await websocket.receive_json()
            await game_manager.handle_action(room_id, player_id, data)
    
    except WebSocketDisconnect:
        game_manager.connection_manager.disconnect(room_id, player_id)
        await game_manager.broadcast_game_state(room_id)


# ============ API 接口 ============

@app.get("/api/rooms")
async def api_rooms():
    """获取房间列表 API"""
    return game_manager.get_room_list()


@app.get("/api/room/{room_id}/state")
async def api_room_state(room_id: str, player_id: Optional[str] = Cookie(None)):
    """获取房间状态 API"""
    if not player_id:
        return {"error": "未登录"}
    state = game_manager.get_game_state_for_player(room_id, player_id)
    if not state:
        return {"error": "房间不存在"}
    return state


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
