"""牌值比较模型"""
from dataclasses import dataclass
from typing import List, Tuple
from src.domain.enums import HandRank
from src.domain.models.card import Card


@dataclass
class HandValue:
    """牌型值，用于比较"""
    rank: HandRank
    kickers: Tuple[int, ...]  # 比较用的踢牌数值
    cards: List[Card]  # 组成牌型的牌

    def __lt__(self, other: 'HandValue') -> bool:
        if self.rank.value != other.rank.value:
            return self.rank.value < other.rank.value
        return self.kickers < other.kickers

    def __gt__(self, other: 'HandValue') -> bool:
        if self.rank.value != other.rank.value:
            return self.rank.value > other.rank.value
        return self.kickers > other.kickers

    def __eq__(self, other: 'HandValue') -> bool:
        return self.rank == other.rank and self.kickers == other.kickers

    def __le__(self, other: 'HandValue') -> bool:
        return self == other or self < other

    def __ge__(self, other: 'HandValue') -> bool:
        return self == other or self > other

    @property
    def display_name(self) -> str:
        """牌型中文名"""
        names = {
            HandRank.HIGH_CARD: "高牌",
            HandRank.PAIR: "一对",
            HandRank.TWO_PAIR: "两对",
            HandRank.THREE_OF_KIND: "三条",
            HandRank.STRAIGHT: "顺子",
            HandRank.FLUSH: "同花",
            HandRank.FULL_HOUSE: "葫芦",
            HandRank.FOUR_OF_KIND: "四条",
            HandRank.STRAIGHT_FLUSH: "同花顺",
            HandRank.ROYAL_FLUSH: "皇家同花顺",
        }
        return names.get(self.rank, str(self.rank))
