"""领域层枚举定义"""
from enum import Enum


class Suit(Enum):
    """花色"""
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"


class HandRank(Enum):
    """牌型等级（从小到大）"""
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10


class BettingMode(Enum):
    """下注模式"""
    LIMIT = "limit"
    NO_LIMIT = "no_limit"
    POT_LIMIT = "pot_limit"

    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            BettingMode.LIMIT: "限注",
            BettingMode.NO_LIMIT: "无限注",
            BettingMode.POT_LIMIT: "彩池限注"
        }
        return names.get(self, self.value)


class GameStage(Enum):
    """游戏阶段"""
    WAITING = "waiting"
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"

    @property
    def display_name(self) -> str:
        """显示名称"""
        names = {
            GameStage.WAITING: "等待中",
            GameStage.PREFLOP: "翻牌前",
            GameStage.FLOP: "翻牌",
            GameStage.TURN: "转牌",
            GameStage.RIVER: "河牌",
            GameStage.SHOWDOWN: "摊牌"
        }
        return names.get(self, self.value)


class PlayerStatus(Enum):
    """玩家状态"""
    WAITING = "waiting"
    ACTIVE = "active"
    FOLDED = "folded"
    ALL_IN = "all_in"


class ActionType(Enum):
    """操作类型"""
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"
