"""游戏服务 - 协调领域层和基础设施层"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable

from src.domain.enums import BettingMode, GameStage, ActionType
from src.domain.models.poker_table import PokerTable
from src.domain.models.player import Player
from src.domain.services.hand_evaluator import HandEvaluator
from src.infrastructure.communication import ConnectionManager
from src.infrastructure.storage import RoomStorage
from src.core.config import settings


@dataclass
class ChatMessage:
    """聊天消息"""
    player_name: str
    content: str
    msg_type: str = "chat"  # chat, system, action
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "player_name": self.player_name,
            "content": self.content,
            "msg_type": self.msg_type,
            "timestamp": self.timestamp
        }


@dataclass
class GameAction:
    """游戏操作记录"""
    player_name: str
    action: str
    amount: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "player": self.player_name,
            "action": self.action,
            "amount": self.amount
        }


class GameService:
    """游戏服务"""

    def __init__(
        self,
        room_storage: RoomStorage,
        connection_manager: ConnectionManager
    ):
        self.room_storage = room_storage
        self.connection_manager = connection_manager

        # 聊天和操作历史
        self.chat_history: Dict[str, List[ChatMessage]] = {}
        self.action_history: Dict[str, List[GameAction]] = {}

        # 计时器
        self.turn_timers: Dict[str, asyncio.Task] = {}
        self.turn_start_time: Dict[str, float] = {}

    # ============ 房间管理 ============

    def create_room(
        self,
        room_name: str,
        mode: BettingMode = BettingMode.NO_LIMIT,
        small_blind: int = 10,
        big_blind: int = 20,
        ante: int = 0
    ) -> PokerTable:
        """创建房间"""
        table = PokerTable(
            room_name=room_name,
            betting_mode=mode,
            small_blind=small_blind,
            big_blind=big_blind,
            ante=ante
        )
        self.room_storage.save(table)
        self.chat_history[table.room_id] = []
        self.action_history[table.room_id] = []
        return table

    def get_room(self, room_id: str) -> Optional[PokerTable]:
        """获取房间"""
        return self.room_storage.get(room_id)

    def get_room_list(self) -> List[dict]:
        """获取房间列表"""
        rooms = self.room_storage.list_all()
        return [
            {
                "id": r.room_id,
                "name": r.room_name,
                "player_count": len(r.players),
                "stage": r.stage.value,
                "mode": r.betting_mode.display_name
            }
            for r in rooms
        ]

    def join_room(
        self,
        room_id: str,
        player_id: str,
        player_name: str
    ) -> bool:
        """加入房间"""
        table = self.get_room(room_id)
        if not table:
            return False

        return table.add_player(
            player_id=player_id,
            player_name=player_name,
            chips=settings.default_chips
        )

    def leave_room(self, room_id: str, player_id: str):
        """离开房间"""
        table = self.get_room(room_id)
        if table:
            table.remove_player(player_id)
            if len(table.players) == 0:
                self.delete_room(room_id)

    def delete_room(self, room_id: str):
        """删除房间"""
        self.room_storage.delete(room_id)
        self.chat_history.pop(room_id, None)
        self.action_history.pop(room_id, None)
        self._cancel_timer(room_id)

    # ============ 游戏流程 ============

    async def start_game(self, room_id: str, player_id: str) -> bool:
        """开始游戏"""
        table = self.get_room(room_id)
        if not table:
            return False

        # 只有房主可以开始
        if table.room_owner != player_id:
            return False

        # 至少2人
        if len(table.players) < 2:
            return False

        # 开始新一手
        if table.start_new_hand():
            self.action_history[room_id] = []
            await self._start_turn_timer(room_id)
            await self.broadcast_chat(room_id, ChatMessage(
                player_name="系统",
                content="新一局开始！",
                msg_type="system"
            ))
            await self.broadcast_game_state(room_id)
            return True

        return False

    async def handle_player_action(
        self,
        room_id: str,
        player_id: str,
        action_data: dict
    ):
        """处理玩家操作"""
        table = self.get_room(room_id)
        if not table:
            return

        action_type = action_data.get("action")

        # 聊天消息单独处理
        if action_type == "chat":
            content = action_data.get("content", "").strip()
            if content:
                player = table.get_player(player_id)
                player_name = player.name if player else "未知"
                await self.broadcast_chat(room_id, ChatMessage(
                    player_name=player_name,
                    content=content[:200],
                    msg_type="chat"
                ))
            return

        # 开始游戏
        if action_type == "start_game":
            await self.start_game(room_id, player_id)
            return

        # 游戏操作
        await self._handle_game_action(room_id, player_id, action_type, action_data)

    async def _handle_game_action(
        self,
        room_id: str,
        player_id: str,
        action_type: str,
        action_data: dict
    ):
        """处理游戏操作"""
        table = self.get_room(room_id)
        if not table:
            return

        # 检查是否轮到该玩家
        current_player = table.get_current_player()
        if not current_player or current_player.id != player_id:
            return

        action_text = ""
        action_amount = 0

        if action_type == "fold":
            current_player.fold()
            action_text = "弃牌"

        elif action_type == "check":
            if not table.can_check(current_player):
                return
            current_player.has_acted = True
            action_text = "过牌"

        elif action_type == "call":
            call_amount = table.can_call(current_player)
            if call_amount > 0:
                actual = current_player.place_bet(call_amount)
                table.pot.add(actual)
                action_text = "跟注"
                action_amount = actual
            else:
                current_player.has_acted = True
                action_text = "过牌"

        elif action_type == "bet":
            if table.current_bet > 0:
                return  # 已有人下注，应该用raise

            min_bet = table.betting_rule.get_min_bet(table.big_blind, table.stage)
            max_bet = table.get_max_raise(current_player)

            bet_amount = action_data.get("amount", min_bet)
            bet_amount = max(min_bet, min(bet_amount, max_bet, current_player.chips))

            actual = current_player.place_bet(bet_amount)
            table.pot.add(actual)
            table.current_bet = current_player.current_bet
            table.last_raise_amount = actual
            table.raise_count += 1
            table.last_raiser_index = current_player.position

            # 重置其他玩家的行动标记
            self._reset_other_players_acted(table, current_player.id)

            action_text = "下注"
            action_amount = actual

        elif action_type == "raise":
            if not table.can_raise():
                return

            min_raise = table.get_min_raise()
            max_raise = table.get_max_raise(current_player)

            if max_raise <= 0:
                return

            raise_amount = action_data.get("amount", min_raise)
            raise_amount = max(min_raise, min(raise_amount, max_raise))

            # 计算需要的筹码：跟注 + 加注
            total_bet = table.current_bet + raise_amount
            need_chips = total_bet - current_player.current_bet

            actual = current_player.place_bet(need_chips)
            table.pot.add(actual)
            table.current_bet = current_player.current_bet
            table.last_raise_amount = raise_amount
            table.raise_count += 1
            table.last_raiser_index = current_player.position

            self._reset_other_players_acted(table, current_player.id)

            action_text = "加注"
            action_amount = actual

        elif action_type == "all_in":
            all_in_amount = current_player.chips
            actual = current_player.place_bet(all_in_amount)
            table.pot.add(actual)

            if current_player.current_bet > table.current_bet:
                # 全押金额超过当前下注，视为加注
                raise_amount = current_player.current_bet - table.current_bet
                table.current_bet = current_player.current_bet
                table.last_raise_amount = raise_amount
                table.raise_count += 1
                table.last_raiser_index = current_player.position
                self._reset_other_players_acted(table, current_player.id)

            action_text = "全押"
            action_amount = actual

        # 记录操作
        if action_text:
            self._add_action(room_id, current_player.name, action_text, action_amount)

        # 检查游戏状态
        await self._check_game_state(room_id, table)

    def _reset_other_players_acted(self, table: PokerTable, exclude_id: str):
        """重置其他玩家的行动标记"""
        for p in table.players:
            if p.id != exclude_id and p.can_act():
                p.has_acted = False

    async def _check_game_state(self, room_id: str, table: PokerTable):
        """检查并推进游戏状态"""
        # 检查是否只剩一个活跃玩家
        active_players = table.get_active_players()
        if len(active_players) == 1:
            await self._handle_single_winner(room_id, table, active_players[0])
            return

        # 检查下注轮是否完成
        if table.is_betting_round_complete():
            players_can_act = table.get_players_can_act()

            # 所有人都全押或只剩一人可行动
            if len(players_can_act) <= 1:
                await self._run_out_cards(room_id, table)
                return

            # 进入下一阶段
            if table.stage == GameStage.RIVER:
                await self._handle_showdown(room_id, table)
                return
            else:
                table.advance_stage()
                stage_names = {
                    GameStage.FLOP: "翻牌",
                    GameStage.TURN: "转牌",
                    GameStage.RIVER: "河牌"
                }
                if table.stage in stage_names:
                    await self.broadcast_chat(room_id, ChatMessage(
                        player_name="系统",
                        content=f"进入{stage_names[table.stage]}阶段",
                        msg_type="system"
                    ))
        else:
            # 移动到下一个玩家
            next_idx = table.get_next_active_player_index(table.current_player_index)
            if next_idx >= 0:
                table.current_player_index = next_idx

        # 重启计时器并广播状态
        await self._start_turn_timer(room_id)
        await self.broadcast_game_state(room_id)

    async def _handle_single_winner(
        self,
        room_id: str,
        table: PokerTable,
        winner: Player
    ):
        """处理只剩一个玩家的情况"""
        self._cancel_timer(room_id)
        table.stage = GameStage.SHOWDOWN
        amount = table.pot.total
        winner.chips += amount

        await self.broadcast_game_state(room_id, winners=[{
            "name": winner.name,
            "amount": amount,
            "hand_name": None
        }])
        await self.broadcast_chat(room_id, ChatMessage(
            player_name="系统",
            content=f"🏆 {winner.name} 赢得 {amount} 筹码！",
            msg_type="system"
        ))
        table.end_hand()

    async def _run_out_cards(self, room_id: str, table: PokerTable):
        """发完所有公共牌并摊牌"""
        self._cancel_timer(room_id)

        while table.stage not in [GameStage.RIVER, GameStage.SHOWDOWN]:
            table.advance_stage()
            stage_names = {
                GameStage.FLOP: "翻牌",
                GameStage.TURN: "转牌",
                GameStage.RIVER: "河牌"
            }
            if table.stage in stage_names:
                await self.broadcast_chat(room_id, ChatMessage(
                    player_name="系统",
                    content=f"进入{stage_names[table.stage]}阶段",
                    msg_type="system"
                ))
                await self.broadcast_game_state(room_id)
                await asyncio.sleep(1)

        await self._handle_showdown(room_id, table)

    async def _handle_showdown(self, room_id: str, table: PokerTable):
        """处理摊牌"""
        self._cancel_timer(room_id)
        table.stage = GameStage.SHOWDOWN

        winners = table.determine_winners()
        winners_data = []
        for w in winners:
            player, amount, hand_value = w
            hand_name = hand_value.display_name if hand_value else "赢家"
            winners_data.append({
                "name": player.name,
                "amount": amount,
                "hand_name": hand_value.rank.name if hand_value else None
            })
            await self.broadcast_chat(room_id, ChatMessage(
                player_name="系统",
                content=f"🏆 {player.name} 以 {hand_name} 赢得 {amount} 筹码！",
                msg_type="system"
            ))

        await self.broadcast_game_state(room_id, winners=winners_data)
        table.end_hand()

    # ============ 计时器 ============

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
            await asyncio.sleep(settings.turn_timeout)
            table = self.get_room(room_id)
            if table and table.stage not in [GameStage.WAITING, GameStage.SHOWDOWN]:
                current_player = table.get_current_player()
                if current_player and current_player.can_act():
                    await self.handle_player_action(
                        room_id,
                        current_player.id,
                        {"action": "fold"}
                    )
                    await self.broadcast_chat(room_id, ChatMessage(
                        player_name="系统",
                        content=f"{current_player.name} 超时自动弃牌",
                        msg_type="system"
                    ))

        self.turn_timers[room_id] = asyncio.create_task(timeout_handler())

    def get_remaining_time(self, room_id: str) -> int:
        """获取剩余时间"""
        if room_id not in self.turn_start_time:
            return settings.turn_timeout
        elapsed = time.time() - self.turn_start_time[room_id]
        return max(0, int(settings.turn_timeout - elapsed))

    # ============ 聊天和历史 ============

    async def broadcast_chat(self, room_id: str, message: ChatMessage):
        """广播聊天消息"""
        if room_id not in self.chat_history:
            self.chat_history[room_id] = []
        self.chat_history[room_id].append(message)

        # 限制历史数量
        if len(self.chat_history[room_id]) > settings.max_chat_history:
            self.chat_history[room_id] = self.chat_history[room_id][-settings.max_chat_history:]

        await self.connection_manager.broadcast_to_room(room_id, {
            "type": "chat",
            "data": message.to_dict()
        })

    def _add_action(self, room_id: str, player_name: str, action: str, amount: int = 0):
        """添加操作记录"""
        if room_id not in self.action_history:
            self.action_history[room_id] = []

        self.action_history[room_id].append(GameAction(
            player_name=player_name,
            action=action,
            amount=amount
        ))

        if len(self.action_history[room_id]) > settings.max_action_history:
            self.action_history[room_id] = self.action_history[room_id][-settings.max_action_history:]

    # ============ 状态广播 ============

    def get_game_state_for_player(self, room_id: str, player_id: str) -> Optional[dict]:
        """获取玩家视角的游戏状态"""
        table = self.get_room(room_id)
        if not table:
            return None

        state = table.to_dict_for_player(player_id)
        state["remaining_time"] = self.get_remaining_time(room_id)
        state["action_history"] = [
            a.to_dict() for a in (self.action_history.get(room_id, []))[-10:]
        ]
        return state

    async def broadcast_game_state(self, room_id: str, winners: list = None):
        """广播游戏状态给房间所有玩家"""
        table = self.get_room(room_id)
        if not table:
            return

        for player in table.players:
            state = self.get_game_state_for_player(room_id, player.id)
            if state:
                if winners:
                    state["winners"] = winners
                await self.connection_manager.send_to_player(
                    room_id,
                    player.id,
                    {"type": "game_state", "data": state}
                )
