"""牌组模型"""
import random
from typing import List, Optional
from src.domain.enums import Suit
from src.domain.models.card import Card, Rank


class Deck:
    """牌组"""

    def __init__(self):
        self._cards: List[Card] = []
        self._burned: List[Card] = []
        self.reset()

    def reset(self):
        """重置牌组"""
        self._cards = []
        self._burned = []
        for suit in Suit:
            for value in range(2, 15):  # 2-A
                self._cards.append(Card(suit=suit, rank=Rank(value)))
        self.shuffle()

    def shuffle(self):
        """洗牌"""
        random.shuffle(self._cards)

    def draw(self, count: int = 1) -> List[Card]:
        """发牌"""
        if count > len(self._cards):
            raise ValueError(f"Not enough cards in deck. Requested {count}, available {len(self._cards)}")
        drawn = self._cards[:count]
        self._cards = self._cards[count:]
        return drawn

    def draw_one(self) -> Optional[Card]:
        """发一张牌"""
        cards = self.draw(1)
        return cards[0] if cards else None

    def burn(self) -> Optional[Card]:
        """烧牌"""
        if self._cards:
            card = self._cards.pop(0)
            self._burned.append(card)
            return card
        return None

    @property
    def remaining(self) -> int:
        """剩余牌数"""
        return len(self._cards)

    @property
    def burned_cards(self) -> List[Card]:
        """已烧的牌"""
        return self._burned.copy()
