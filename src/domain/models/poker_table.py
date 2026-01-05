"""牌桌/游戏状态模型"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import uuid

from src.domain.enums import BettingMode, GameStage
from src.domain.models.card import Card
from src.domain.models.deck import Deck
from src.domain.models.player import Player
from src.domain.models.pot import Pot
from src.domain.models.hand_value import HandValue
from src.domain.rules.betting_rules import BettingRule, BettingRuleFactory
from src.domain.services.hand_evaluator import HandEvaluator


@dataclass
class PokerTable:
    """德州扑克牌桌"""

    # 房间信息
    room_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    room_name: str = "德州扑克"
    room_owner: Optional[str] = None  # 房主玩家ID

    # 游戏配置
    small_blind: int = 10
    big_blind: int = 20
    ante: int = 0
    max_players: int = 10

    # 下注规则
    betting_mode: BettingMode = BettingMode.NO_LIMIT
    betting_rule: BettingRule = field(default=None)

    # 游戏状态
    stage: GameStage = GameStage.WAITING
    players: List[Player] = field(default_factory=list)
    deck: Deck = field(default_factory=Deck)
    community_cards: List[Card] = field(default_factory=list)
    pot: Pot = field(default_factory=Pot)

    # 位置信息
    dealer_position: int = 0
    current_player_index: int = 0

    # 下注状态
    current_bet: int = 0  # 当前轮最高下注
    last_raise_amount: int = 0  # 上次加注的增量
    raise_count: int = 0  # 当前轮加注次数
    last_raiser_index: int = -1  # 最后加注者位置

    def __post_init__(self):
        if self.betting_rule is None:
            self.betting_rule = BettingRuleFactory.create(self.betting_mode)

    # ============ 玩家管理 ============

    def add_player(self, player_id: str, player_name: str, chips: int = 1000) -> bool:
        """添加玩家"""
        if len(self.players) >= self.max_players:
            return False

        # 检查是否已存在
        for p in self.players:
            if p.id == player_id:
                return True

        player = Player(
            id=player_id,
            name=player_name,
            chips=chips,
            position=len(self.players)
        )
        self.players.append(player)

        # 第一个玩家成为房主
        if self.room_owner is None:
            self.room_owner = player_id

        return True

    def remove_player(self, player_id: str):
        """移除玩家"""
        for i, p in enumerate(self.players):
            if p.id == player_id:
                self.players.pop(i)
                # 更新后续玩家位置
                for j in range(i, len(self.players)):
                    self.players[j].position = j
                # 如果是房主离开，转移给下一个玩家
                if self.room_owner == player_id and self.players:
                    self.room_owner = self.players[0].id
                break

    def get_player(self, player_id: str) -> Optional[Player]:
        """获取玩家"""
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def get_current_player(self) -> Optional[Player]:
        """获取当前行动玩家"""
        if 0 <= self.current_player_index < len(self.players):
            return self.players[self.current_player_index]
        return None

    # ============ 游戏流程 ============

    def start_new_hand(self):
        """开始新一手"""
        if len(self.players) < 2:
            return False

        # 重置牌组
        self.deck.reset()

        # 重置底池
        self.pot.reset()

        # 清空公共牌
        self.community_cards = []

        # 重置下注状态
        self.current_bet = 0
        self.last_raise_amount = self.big_blind
        self.raise_count = 0
        self.last_raiser_index = -1

        # 重置玩家
        for p in self.players:
            p.reset_for_new_hand()

        # 发手牌
        for _ in range(2):
            for p in self.players:
                card = self.deck.draw_one()
                if card:
                    p.hand.append(card)

        # 设置阶段
        self.stage = GameStage.PREFLOP

        # 收前注
        if self.ante > 0:
            for p in self.players:
                ante_amount = p.place_bet(self.ante)
                self.pot.add(ante_amount)

        # 收盲注
        self._post_blinds()

        return True

    def _post_blinds(self):
        """收盲注"""
        num_players = len(self.players)
        if num_players < 2:
            return

        if num_players == 2:
            # 单挑：庄家下小盲，对手下大盲
            sb_pos = self.dealer_position
            bb_pos = (self.dealer_position + 1) % num_players
        else:
            # 多人：庄家后一位小盲，再后一位大盲
            sb_pos = (self.dealer_position + 1) % num_players
            bb_pos = (self.dealer_position + 2) % num_players

        # 小盲
        sb_player = self.players[sb_pos]
        sb_amount = sb_player.place_bet(self.small_blind)
        self.pot.add(sb_amount)

        # 大盲
        bb_player = self.players[bb_pos]
        bb_amount = bb_player.place_bet(self.big_blind)
        self.pot.add(bb_amount)

        # 设置当前下注额
        self.current_bet = self.big_blind
        self.last_raise_amount = self.big_blind

        # 设置首个行动玩家（大盲后一位）
        if num_players == 2:
            self.current_player_index = self.dealer_position
        else:
            self.current_player_index = (bb_pos + 1) % num_players

    def advance_stage(self):
        """进入下一阶段"""
        # 重置下注状态
        self.current_bet = 0
        self.last_raise_amount = self.big_blind
        self.raise_count = 0

        for p in self.players:
            p.reset_for_new_round()

        # 发公共牌
        if self.stage == GameStage.PREFLOP:
            self.stage = GameStage.FLOP
            self.deck.burn()
            self.community_cards.extend(self.deck.draw(3))
        elif self.stage == GameStage.FLOP:
            self.stage = GameStage.TURN
            self.deck.burn()
            self.community_cards.extend(self.deck.draw(1))
        elif self.stage == GameStage.TURN:
            self.stage = GameStage.RIVER
            self.deck.burn()
            self.community_cards.extend(self.deck.draw(1))
        elif self.stage == GameStage.RIVER:
            self.stage = GameStage.SHOWDOWN

        # 设置首个行动玩家（庄家后第一个活跃玩家）
        self._set_first_to_act()

    def _set_first_to_act(self):
        """设置首个行动玩家"""
        num_players = len(self.players)
        start_pos = (self.dealer_position + 1) % num_players

        for i in range(num_players):
            pos = (start_pos + i) % num_players
            player = self.players[pos]
            if player.can_act():
                self.current_player_index = pos
                return

    # ============ 下注操作 ============

    def get_min_raise(self) -> int:
        """获取最小加注额"""
        return self.betting_rule.get_min_raise(
            self.big_blind, self.stage, self.last_raise_amount
        )

    def get_max_raise(self, player: Player) -> int:
        """获取最大加注额"""
        if not self.betting_rule.can_raise(self.raise_count):
            return 0

        return self.betting_rule.get_max_raise(
            player,
            self.current_bet,
            self.pot.total,
            self.big_blind,
            self.stage
        )

    def can_check(self, player: Player) -> bool:
        """是否可以过牌"""
        return player.current_bet >= self.current_bet

    def can_call(self, player: Player) -> int:
        """获取跟注金额，0表示不需要跟注"""
        return max(0, self.current_bet - player.current_bet)

    def can_raise(self) -> bool:
        """当前轮是否还可以加注"""
        return self.betting_rule.can_raise(self.raise_count)

    # ============ 玩家位置 ============

    def get_active_players(self) -> List[Player]:
        """获取未弃牌的玩家"""
        return [p for p in self.players if not p.folded]

    def get_players_can_act(self) -> List[Player]:
        """获取可以行动的玩家（未弃牌且未全押）"""
        return [p for p in self.players if p.can_act()]

    def get_next_active_player_index(self, current_pos: int) -> int:
        """获取下一个可行动玩家的位置"""
        num_players = len(self.players)
        for i in range(1, num_players + 1):
            next_pos = (current_pos + i) % num_players
            player = self.players[next_pos]
            if player.can_act():
                return next_pos
        return -1

    def is_betting_round_complete(self) -> bool:
        """检查下注轮是否完成"""
        active_players = [p for p in self.players if not p.folded and not p.all_in]

        # 如果只剩0-1个可行动玩家，下注轮完成
        if len(active_players) <= 1:
            return True

        # 检查所有可行动玩家是否都已行动且下注额相同
        for p in active_players:
            if not p.has_acted:
                return False
            if p.current_bet != self.current_bet:
                return False

        return True

    # ============ 结算 ============

    def determine_winners(self) -> List[Tuple[Player, int, HandValue]]:
        """
        确定赢家并分配底池

        返回: [(玩家, 赢得金额, 牌型), ...]
        """
        active_players = self.get_active_players()

        # 只剩一个玩家，直接获胜
        if len(active_players) == 1:
            winner = active_players[0]
            amount = self.pot.total
            winner.chips += amount
            return [(winner, amount, None)]

        # 计算每个玩家的牌力
        player_hands: Dict[str, HandValue] = {}
        for p in active_players:
            all_cards = p.hand + self.community_cards
            if len(all_cards) >= 5:
                player_hands[p.id] = HandEvaluator.evaluate(all_cards)

        # 简化版底池分配（暂不处理边池）
        # 找出最强牌
        best_value = None
        for pid, hv in player_hands.items():
            if best_value is None or hv > best_value:
                best_value = hv

        # 找出所有拥有最强牌的玩家
        winners = []
        for p in active_players:
            if p.id in player_hands and player_hands[p.id] == best_value:
                winners.append(p)

        # 平分底池
        pot_per_winner = self.pot.total // len(winners)
        remainder = self.pot.total % len(winners)

        results = []
        for i, winner in enumerate(winners):
            # 余数给第一个赢家
            amount = pot_per_winner + (remainder if i == 0 else 0)
            winner.chips += amount
            results.append((winner, amount, player_hands.get(winner.id)))

        return results

    def end_hand(self):
        """结束当前手牌"""
        self.stage = GameStage.WAITING
        # 移动庄家位置
        self.dealer_position = (self.dealer_position + 1) % len(self.players)
        # 移除筹码为0的玩家（可选）
        # self.players = [p for p in self.players if p.chips > 0]

    def get_sb_position(self) -> int:
        """获取小盲位置"""
        if len(self.players) < 2:
            return -1
        if len(self.players) == 2:
            return self.dealer_position
        return (self.dealer_position + 1) % len(self.players)

    def get_bb_position(self) -> int:
        """获取大盲位置"""
        if len(self.players) < 2:
            return -1
        if len(self.players) == 2:
            return (self.dealer_position + 1) % len(self.players)
        return (self.dealer_position + 2) % len(self.players)

    # ============ 序列化 ============

    def to_dict_for_player(self, player_id: str) -> Dict[str, Any]:
        """生成玩家视角的游戏状态"""
        player = self.get_player(player_id)
        is_showdown = self.stage == GameStage.SHOWDOWN

        # 构建玩家列表
        players_data = []
        for p in self.players:
            is_self = p.id == player_id
            show_hand = is_showdown and not p.folded
            p_dict = p.to_dict(is_self=is_self, show_hand=show_hand)
            p_dict["is_dealer"] = p.position == self.dealer_position
            p_dict["is_current"] = p.position == self.current_player_index
            p_dict["is_sb"] = p.position == self.get_sb_position()
            p_dict["is_bb"] = p.position == self.get_bb_position()
            players_data.append(p_dict)

        # 计算当前玩家的操作信息
        to_call = 0
        min_raise = self.get_min_raise()
        max_raise = 0
        if player:
            to_call = self.can_call(player)
            max_raise = self.get_max_raise(player)

        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "stage": self.stage.value,
            "betting_mode": self.betting_mode.value,
            "community_cards": [c.to_dict() for c in self.community_cards],
            "main_pot": self.pot.total,
            "current_bet": self.current_bet,
            "min_raise": min_raise,
            "max_raise": max_raise,
            "has_bet_this_round": self.current_bet > 0,
            "to_call": to_call,
            "raise_count": self.raise_count,
            "max_raises": self.betting_rule.max_raises_per_round,
            "can_raise": self.can_raise(),
            "dealer_position": self.dealer_position,
            "current_player_index": self.current_player_index,
            "players": players_data,
            "is_my_turn": (
                player is not None and
                self.current_player_index == player.position and
                self.stage not in [GameStage.WAITING, GameStage.SHOWDOWN]
            ),
            "is_room_owner": self.room_owner == player_id,
            "can_start": len(self.players) >= 2 and self.stage == GameStage.WAITING,
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "ante": self.ante,
        }
