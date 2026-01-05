"""玩家模型"""
from dataclasses import dataclass, field
from typing import List, Optional
from src.domain.enums import PlayerStatus
from src.domain.models.card import Card


@dataclass
class Player:
    """玩家"""
    id: str
    name: str
    chips: int = 1000
    position: int = 0

    # 当前手牌
    hand: List[Card] = field(default_factory=list)

    # 状态
    status: PlayerStatus = PlayerStatus.WAITING
    folded: bool = False
    all_in: bool = False

    # 下注信息
    current_bet: int = 0  # 当前轮下注
    total_bet: int = 0  # 本手总下注
    has_acted: bool = False  # 本轮是否已行动

    def reset_for_new_hand(self):
        """新一手开始时重置"""
        self.hand = []
        self.status = PlayerStatus.ACTIVE
        self.folded = False
        self.all_in = False
        self.current_bet = 0
        self.total_bet = 0
        self.has_acted = False

    def reset_for_new_round(self):
        """新一轮下注开始时重置"""
        self.current_bet = 0
        self.has_acted = False if not self.folded and not self.all_in else True

    def fold(self):
        """弃牌"""
        self.folded = True
        self.status = PlayerStatus.FOLDED
        self.has_acted = True

    def place_bet(self, amount: int) -> int:
        """下注，返回实际下注金额"""
        actual_amount = min(amount, self.chips)
        self.chips -= actual_amount
        self.current_bet += actual_amount
        self.total_bet += actual_amount

        if self.chips == 0:
            self.all_in = True
            self.status = PlayerStatus.ALL_IN

        self.has_acted = True
        return actual_amount

    def can_act(self) -> bool:
        """是否可以行动"""
        return not self.folded and not self.all_in

    @property
    def is_active(self) -> bool:
        """是否还在游戏中（未弃牌）"""
        return not self.folded

    def to_dict(self, is_self: bool = False, show_hand: bool = False) -> dict:
        """转换为字典（用于前端）"""
        result = {
            "id": self.id,
            "name": self.name,
            "chips": self.chips,
            "position": self.position,
            "current_bet": self.current_bet,
            "total_bet": self.total_bet,
            "folded": self.folded,
            "all_in": self.all_in,
            "is_self": is_self,
        }

        # 手牌显示逻辑
        if is_self or show_hand:
            result["hand"] = [c.to_dict() for c in self.hand]
        elif self.hand:
            result["hand"] = [{"hidden": True}, {"hidden": True}]
        else:
            result["hand"] = []

        return result
