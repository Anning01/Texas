"""德州扑克游戏核心逻辑"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional
import random


class Suit(Enum):
    """花色"""
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"


class Rank(Enum):
    """牌面大小"""
    TWO = (2, "2")
    THREE = (3, "3")
    FOUR = (4, "4")
    FIVE = (5, "5")
    SIX = (6, "6")
    SEVEN = (7, "7")
    EIGHT = (8, "8")
    NINE = (9, "9")
    TEN = (10, "10")
    JACK = (11, "J")
    QUEEN = (12, "Q")
    KING = (13, "K")
    ACE = (14, "A")

    def __init__(self, num_value, display):
        self._num_value = num_value
        self._display = display

    @property
    def num_value(self):
        return self._num_value

    @property
    def display(self):
        return self._display


@dataclass
class Card:
    """扑克牌"""
    suit: Suit
    rank: Rank

    def __str__(self):
        return f"{self.rank.display}{self.suit.value}"

    def __repr__(self):
        return str(self)


class HandRank(Enum):
    """牌型等级"""
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


@dataclass
class HandValue:
    """手牌价值"""
    rank: HandRank
    values: List[int]  # 用于比较的值列表

    def __lt__(self, other):
        if self.rank != other.rank:
            return self.rank.value < other.rank.value
        return self.values < other.values

    def __gt__(self, other):
        if self.rank != other.rank:
            return self.rank.value > other.rank.value
        return self.values > other.values

    def __eq__(self, other):
        return self.rank == other.rank and self.values == other.values


class Deck:
    """牌堆"""
    def __init__(self):
        self.cards: List[Card] = []
        self.reset()

    def reset(self):
        """重置牌堆"""
        self.cards = [Card(suit, rank) for suit in Suit for rank in Rank]
        random.shuffle(self.cards)

    def draw(self) -> Optional[Card]:
        """抽一张牌"""
        return self.cards.pop() if self.cards else None

    def burn(self):
        """销牌"""
        if self.cards:
            self.cards.pop()


class HandEvaluator:
    """手牌评估器"""

    @staticmethod
    def evaluate(cards: List[Card]) -> HandValue:
        """评估手牌价值(从7张牌中选最好的5张)"""
        if len(cards) < 5:
            return HandValue(HandRank.HIGH_CARD, [0])

        # 如果是7张牌,尝试所有21种5张牌组合
        if len(cards) == 7:
            from itertools import combinations
            best_hand = None
            for combo in combinations(cards, 5):
                hand_value = HandEvaluator._evaluate_5_cards(list(combo))
                if best_hand is None or hand_value > best_hand:
                    best_hand = hand_value
            return best_hand
        else:
            return HandEvaluator._evaluate_5_cards(cards)

    @staticmethod
    def _evaluate_5_cards(cards: List[Card]) -> HandValue:
        """评估5张牌的价值"""
        ranks = sorted([card.rank.num_value for card in cards], reverse=True)
        suits = [card.suit for card in cards]

        # 检查是否同花
        is_flush = len(set(suits)) == 1

        # 检查是否顺子
        is_straight = False
        straight_high = 0

        # 正常顺子
        if ranks == list(range(ranks[0], ranks[0]-5, -1)):
            is_straight = True
            straight_high = ranks[0]
        # A-2-3-4-5 特殊顺子
        elif ranks == [14, 5, 4, 3, 2]:
            is_straight = True
            straight_high = 5

        # 统计各牌面数量
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1

        counts = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
        count_values = [count for _, count in counts]
        rank_values = [rank for rank, _ in counts]

        # 皇家同花顺
        if is_flush and is_straight and straight_high == 14:
            return HandValue(HandRank.ROYAL_FLUSH, [14])

        # 同花顺
        if is_flush and is_straight:
            return HandValue(HandRank.STRAIGHT_FLUSH, [straight_high])

        # 四条
        if count_values == [4, 1]:
            return HandValue(HandRank.FOUR_OF_KIND, rank_values)

        # 葫芦
        if count_values == [3, 2]:
            return HandValue(HandRank.FULL_HOUSE, rank_values)

        # 同花
        if is_flush:
            return HandValue(HandRank.FLUSH, ranks)

        # 顺子
        if is_straight:
            return HandValue(HandRank.STRAIGHT, [straight_high])

        # 三条
        if count_values == [3, 1, 1]:
            return HandValue(HandRank.THREE_OF_KIND, rank_values)

        # 两对
        if count_values == [2, 2, 1]:
            return HandValue(HandRank.TWO_PAIR, rank_values)

        # 一对
        if count_values == [2, 1, 1, 1]:
            return HandValue(HandRank.PAIR, rank_values)

        # 高牌
        return HandValue(HandRank.HIGH_CARD, ranks)

    @staticmethod
    def get_hand_name(hand_value: HandValue) -> str:
        """获取牌型名称"""
        rank_names = {
            HandRank.HIGH_CARD: "高牌",
            HandRank.PAIR: "一对",
            HandRank.TWO_PAIR: "两对",
            HandRank.THREE_OF_KIND: "三条",
            HandRank.STRAIGHT: "顺子",
            HandRank.FLUSH: "同花",
            HandRank.FULL_HOUSE: "葫芦",
            HandRank.FOUR_OF_KIND: "四条",
            HandRank.STRAIGHT_FLUSH: "同花顺",
            HandRank.ROYAL_FLUSH: "皇家同花顺"
        }
        return rank_names.get(hand_value.rank, "未知")


class BettingMode(Enum):
    """下注模式"""
    LIMIT = "限注"
    NO_LIMIT = "无限注"
    POT_LIMIT = "彩池限注"


class GameStage(Enum):
    """游戏阶段"""
    WAITING = "等待开始"
    PREFLOP = "翻牌前"
    FLOP = "翻牌圈"
    TURN = "转牌圈"
    RIVER = "河牌圈"
    SHOWDOWN = "摊牌"
    ENDED = "结束"


@dataclass
class Player:
    """玩家"""
    id: str
    name: str
    chips: int
    hand: List[Card]
    current_bet: int
    total_bet: int  # 本轮总下注
    folded: bool
    all_in: bool
    position: int  # 座位位置

    def reset_for_new_hand(self):
        """新一手牌重置"""
        self.hand = []
        self.current_bet = 0
        self.total_bet = 0
        self.folded = False
        self.all_in = False


@dataclass
class Pot:
    """底池"""
    amount: int
    eligible_players: List[str]  # 有资格赢得此底池的玩家ID


class GameState:
    """游戏状态"""
    def __init__(self, betting_mode: BettingMode = BettingMode.LIMIT):
        self.betting_mode = betting_mode
        self.small_blind = 10
        self.big_blind = 20
        self.stage = GameStage.WAITING
        self.dealer_position = 0
        self.current_player_index = 0
        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.pots: List[Pot] = []
        self.main_pot = 0
        self.current_bet = 0
        self.min_raise = self.big_blind
        self.players: List[Player] = []
        self.room_owner: Optional[str] = None
        self.last_raiser_index = -1

    def add_player(self, player_id: str, player_name: str, chips: int = 1000):
        """添加玩家"""
        player = Player(
            id=player_id,
            name=player_name,
            chips=chips,
            hand=[],
            current_bet=0,
            total_bet=0,
            folded=False,
            all_in=False,
            position=len(self.players)
        )
        self.players.append(player)
        if self.room_owner is None:
            self.room_owner = player_id

    def remove_player(self, player_id: str):
        """移除玩家"""
        self.players = [p for p in self.players if p.id != player_id]
        # 重新分配位置
        for i, player in enumerate(self.players):
            player.position = i

    def start_new_hand(self):
        """开始新一手牌"""
        if len(self.players) < 2:
            return False

        # 重置牌堆和公共牌
        self.deck.reset()
        self.community_cards = []
        self.pots = []
        self.main_pot = 0
        self.current_bet = 0
        self.min_raise = self.big_blind
        self.last_raiser_index = -1

        # 重置玩家状态
        for player in self.players:
            player.reset_for_new_hand()

        # 发底牌
        for _ in range(2):
            for player in self.players:
                if not player.folded:
                    card = self.deck.draw()
                    if card:
                        player.hand.append(card)

        # 设置盲注
        self._post_blinds()

        self.stage = GameStage.PREFLOP
        # 翻牌前从大盲注下家开始
        self.current_player_index = (self.dealer_position + 3) % len(self.players)

        return True

    def _post_blinds(self):
        """下盲注"""
        num_players = len(self.players)
        if num_players == 2:
            # 一对一: 庄家下小盲注,对手下大盲注
            small_blind_idx = self.dealer_position
            big_blind_idx = (self.dealer_position + 1) % num_players
        else:
            small_blind_idx = (self.dealer_position + 1) % num_players
            big_blind_idx = (self.dealer_position + 2) % num_players

        # 小盲注
        sb_player = self.players[small_blind_idx]
        sb_amount = min(self.small_blind, sb_player.chips)
        sb_player.chips -= sb_amount
        sb_player.current_bet = sb_amount
        sb_player.total_bet = sb_amount
        self.main_pot += sb_amount

        if sb_player.chips == 0:
            sb_player.all_in = True

        # 大盲注
        bb_player = self.players[big_blind_idx]
        bb_amount = min(self.big_blind, bb_player.chips)
        bb_player.chips -= bb_amount
        bb_player.current_bet = bb_amount
        bb_player.total_bet = bb_amount
        self.main_pot += bb_amount
        self.current_bet = bb_amount

        if bb_player.chips == 0:
            bb_player.all_in = True

    def get_active_players(self) -> List[Player]:
        """获取未弃牌的玩家"""
        return [p for p in self.players if not p.folded]

    def get_next_active_player_index(self, start_index: int) -> int:
        """获取下一个未弃牌且未全押的玩家索引"""
        num_players = len(self.players)
        for i in range(1, num_players + 1):
            idx = (start_index + i) % num_players
            player = self.players[idx]
            if not player.folded and not player.all_in:
                return idx
        return -1

    def is_betting_round_complete(self) -> bool:
        """判断下注轮是否完成"""
        active_players = [p for p in self.players if not p.folded and not p.all_in]

        # 如果只剩一个或没有活跃玩家,结束
        if len(active_players) <= 1:
            return True

        # 所有活跃玩家下注相同
        if len(active_players) > 0:
            target_bet = self.current_bet
            for player in active_players:
                if player.current_bet != target_bet:
                    return False

        return True

    def advance_stage(self):
        """进入下一阶段"""
        # 重置当前下注
        for player in self.players:
            player.current_bet = 0
        self.current_bet = 0
        self.last_raiser_index = -1

        if self.stage == GameStage.PREFLOP:
            # 发翻牌
            self.deck.burn()
            for _ in range(3):
                card = self.deck.draw()
                if card:
                    self.community_cards.append(card)
            self.stage = GameStage.FLOP
        elif self.stage == GameStage.FLOP:
            # 发转牌
            self.deck.burn()
            card = self.deck.draw()
            if card:
                self.community_cards.append(card)
            self.stage = GameStage.TURN
        elif self.stage == GameStage.TURN:
            # 发河牌
            self.deck.burn()
            card = self.deck.draw()
            if card:
                self.community_cards.append(card)
            self.stage = GameStage.RIVER
        elif self.stage == GameStage.RIVER:
            self.stage = GameStage.SHOWDOWN
            return

        # 翻牌后从庄家下家第一个未弃牌玩家开始
        self.current_player_index = self.get_next_active_player_index(self.dealer_position)

    def determine_winners(self) -> List[Tuple[Player, int, HandValue]]:
        """确定赢家并分配底池"""
        active_players = self.get_active_players()

        if len(active_players) == 0:
            return []

        if len(active_players) == 1:
            # 只有一个玩家未弃牌
            winner = active_players[0]
            winner.chips += self.main_pot
            return [(winner, self.main_pot, HandValue(HandRank.HIGH_CARD, [0]))]

        # 计算边池
        self._calculate_side_pots()

        # 评估每个玩家的手牌
        player_hands = {}
        for player in active_players:
            all_cards = player.hand + self.community_cards
            hand_value = HandEvaluator.evaluate(all_cards)
            player_hands[player.id] = hand_value

        # 分配每个底池
        results = []
        for pot in self.pots:
            # 找出有资格获得此底池的最佳手牌
            eligible = [p for p in active_players if p.id in pot.eligible_players]
            if not eligible:
                continue

            best_hand = max([player_hands[p.id] for p in eligible])
            winners = [p for p in eligible if player_hands[p.id] == best_hand]

            # 平分底池
            share = pot.amount // len(winners)
            remainder = pot.amount % len(winners)

            # 找到最接近庄家顺时针方向的赢家获得余数
            closest_winner = None
            if remainder > 0:
                closest_winner = min(winners,
                                   key=lambda p: (p.position - self.dealer_position - 1) % len(self.players))
                closest_winner.chips += remainder

            for winner in winners:
                winner.chips += share
                results.append((winner, share + (remainder if closest_winner and winner == closest_winner else 0), player_hands[winner.id]))

        return results

    def _calculate_side_pots(self):
        """计算主池和边池"""
        active_players = self.get_active_players()

        # 按总下注排序
        sorted_players = sorted(active_players, key=lambda p: p.total_bet)

        self.pots = []
        remaining_bets = {p.id: p.total_bet for p in active_players}

        for i, player in enumerate(sorted_players):
            if player.total_bet == 0:
                continue

            # 计算此玩家能参与的底池
            bet_level = player.total_bet
            pot_amount = 0
            eligible = []

            for p in active_players:
                if remaining_bets[p.id] > 0:
                    contribution = min(remaining_bets[p.id], bet_level)
                    pot_amount += contribution
                    remaining_bets[p.id] -= contribution
                    if contribution > 0:
                        eligible.append(p.id)

            if pot_amount > 0:
                self.pots.append(Pot(amount=pot_amount, eligible_players=eligible))

    def end_hand(self):
        """结束当前手牌"""
        # 移动庄家位置
        self.dealer_position = (self.dealer_position + 1) % len(self.players)
        self.stage = GameStage.WAITING
