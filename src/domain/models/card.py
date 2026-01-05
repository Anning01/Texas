"""扑克牌模型"""
from dataclasses import dataclass
from typing import Tuple
from src.domain.enums import Suit


class Rank:
    """牌点数"""

    # 点数定义: (数值, 显示字符)
    RANK_DATA = {
        2: (2, "2"),
        3: (3, "3"),
        4: (4, "4"),
        5: (5, "5"),
        6: (6, "6"),
        7: (7, "7"),
        8: (8, "8"),
        9: (9, "9"),
        10: (10, "10"),
        11: (11, "J"),
        12: (12, "Q"),
        13: (13, "K"),
        14: (14, "A"),
    }

    def __init__(self, value: int):
        if value not in self.RANK_DATA:
            raise ValueError(f"Invalid rank value: {value}")
        self._value = value
        self._num_value, self._display = self.RANK_DATA[value]

    @property
    def value(self) -> int:
        return self._value

    @property
    def num_value(self) -> int:
        """数值（用于比较）"""
        return self._num_value

    @property
    def display(self) -> str:
        """显示字符"""
        return self._display

    def __eq__(self, other):
        if isinstance(other, Rank):
            return self._value == other._value
        return False

    def __lt__(self, other):
        if isinstance(other, Rank):
            return self._value < other._value
        return NotImplemented

    def __hash__(self):
        return hash(self._value)

    def __repr__(self):
        return f"Rank({self._display})"


@dataclass(frozen=True)
class Card:
    """扑克牌"""
    suit: Suit
    rank: Rank

    @property
    def color(self) -> str:
        """牌的颜色"""
        return "red" if self.suit in [Suit.HEARTS, Suit.DIAMONDS] else "black"

    def to_dict(self) -> dict:
        """转换为字典（用于前端显示）"""
        return {
            "suit": self.suit.value,
            "rank": self.rank.display,
            "color": self.color
        }

    def __str__(self):
        return f"{self.rank.display}{self.suit.value}"

    def __repr__(self):
        return f"Card({self.rank.display}{self.suit.value})"
