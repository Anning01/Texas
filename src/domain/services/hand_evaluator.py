"""手牌评估服务"""
from itertools import combinations
from typing import List, Tuple
from collections import Counter

from src.domain.enums import HandRank, Suit
from src.domain.models.card import Card
from src.domain.models.hand_value import HandValue


class HandEvaluator:
    """手牌评估器"""

    @staticmethod
    def evaluate(cards: List[Card]) -> HandValue:
        """
        评估最佳5张牌组合

        参数:
            cards: 7张牌（2张手牌+5张公共牌）
        返回:
            HandValue: 最佳牌型
        """
        if len(cards) < 5:
            raise ValueError(f"Need at least 5 cards, got {len(cards)}")

        if len(cards) == 5:
            return HandEvaluator._evaluate_5_cards(cards)

        # 从7张牌中选5张的最佳组合
        best_value = None
        for combo in combinations(cards, 5):
            value = HandEvaluator._evaluate_5_cards(list(combo))
            if best_value is None or value > best_value:
                best_value = value

        return best_value

    @staticmethod
    def _evaluate_5_cards(cards: List[Card]) -> HandValue:
        """评估5张牌的牌型"""
        if len(cards) != 5:
            raise ValueError(f"Expected 5 cards, got {len(cards)}")

        # 排序（按点数降序）
        sorted_cards = sorted(cards, key=lambda c: c.rank.num_value, reverse=True)
        ranks = [c.rank.num_value for c in sorted_cards]
        suits = [c.suit for c in sorted_cards]

        # 统计点数出现次数
        rank_counts = Counter(ranks)
        count_values = sorted(rank_counts.values(), reverse=True)

        # 检查同花
        is_flush = len(set(suits)) == 1

        # 检查顺子
        is_straight = False
        straight_high = 0
        unique_ranks = sorted(set(ranks), reverse=True)

        if len(unique_ranks) == 5:
            # 普通顺子
            if unique_ranks[0] - unique_ranks[4] == 4:
                is_straight = True
                straight_high = unique_ranks[0]
            # A-2-3-4-5 特殊顺子（A视为1）
            elif unique_ranks == [14, 5, 4, 3, 2]:
                is_straight = True
                straight_high = 5

        # 判断牌型
        if is_straight and is_flush:
            if straight_high == 14 and 13 in ranks:  # A-K-Q-J-10
                return HandValue(HandRank.ROYAL_FLUSH, (14,), sorted_cards)
            return HandValue(HandRank.STRAIGHT_FLUSH, (straight_high,), sorted_cards)

        if count_values == [4, 1]:
            # 四条
            quad_rank = [r for r, c in rank_counts.items() if c == 4][0]
            kicker = [r for r, c in rank_counts.items() if c == 1][0]
            return HandValue(HandRank.FOUR_OF_KIND, (quad_rank, kicker), sorted_cards)

        if count_values == [3, 2]:
            # 葫芦
            triple_rank = [r for r, c in rank_counts.items() if c == 3][0]
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            return HandValue(HandRank.FULL_HOUSE, (triple_rank, pair_rank), sorted_cards)

        if is_flush:
            return HandValue(HandRank.FLUSH, tuple(ranks), sorted_cards)

        if is_straight:
            return HandValue(HandRank.STRAIGHT, (straight_high,), sorted_cards)

        if count_values == [3, 1, 1]:
            # 三条
            triple_rank = [r for r, c in rank_counts.items() if c == 3][0]
            kickers = sorted([r for r, c in rank_counts.items() if c == 1], reverse=True)
            return HandValue(HandRank.THREE_OF_KIND, (triple_rank,) + tuple(kickers), sorted_cards)

        if count_values == [2, 2, 1]:
            # 两对
            pairs = sorted([r for r, c in rank_counts.items() if c == 2], reverse=True)
            kicker = [r for r, c in rank_counts.items() if c == 1][0]
            return HandValue(HandRank.TWO_PAIR, tuple(pairs) + (kicker,), sorted_cards)

        if count_values == [2, 1, 1, 1]:
            # 一对
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            kickers = sorted([r for r, c in rank_counts.items() if c == 1], reverse=True)
            return HandValue(HandRank.PAIR, (pair_rank,) + tuple(kickers), sorted_cards)

        # 高牌
        return HandValue(HandRank.HIGH_CARD, tuple(ranks), sorted_cards)

    @staticmethod
    def get_hand_name(hand_value: HandValue) -> str:
        """获取牌型中文名称"""
        return hand_value.display_name
