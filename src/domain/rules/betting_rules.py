"""下注规则

根据德州扑克核心玩法对比文档实现三种下注模式：
- 无限注（No-Limit）：下注/加注无金额限制，仅受筹码约束
- 限注（Limit）：下注/加注金额固定，每轮最多3-4次加注
- 彩池限制（Pot-Limit）：最大加注额不超过当前彩池大小
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.domain.enums import BettingMode, GameStage

if TYPE_CHECKING:
    from src.domain.models.player import Player


class BettingRule(ABC):
    """下注规则基类"""

    @property
    @abstractmethod
    def mode(self) -> BettingMode:
        """下注模式"""
        pass

    @property
    @abstractmethod
    def max_raises_per_round(self) -> int:
        """每轮最大加注次数（0表示无限制）"""
        pass

    @abstractmethod
    def get_min_bet(self, big_blind: int, stage: GameStage) -> int:
        """获取最小下注额"""
        pass

    @abstractmethod
    def get_min_raise(self, big_blind: int, stage: GameStage, last_raise_amount: int) -> int:
        """
        获取最小加注额（加注增量，不是总金额）

        参数:
            big_blind: 大盲注
            stage: 当前阶段
            last_raise_amount: 上次加注的增量
        """
        pass

    @abstractmethod
    def get_max_raise(
        self,
        player: 'Player',
        current_bet: int,
        pot_total: int,
        big_blind: int,
        stage: GameStage
    ) -> int:
        """
        获取最大加注额（加注增量，不是总金额）

        参数:
            player: 当前玩家
            current_bet: 当前轮最高下注
            pot_total: 底池总额
            big_blind: 大盲注
            stage: 当前阶段
        """
        pass

    def can_raise(self, raise_count: int) -> bool:
        """是否还可以加注"""
        if self.max_raises_per_round == 0:
            return True
        return raise_count < self.max_raises_per_round


class NoLimitRule(BettingRule):
    """
    无限注规则

    - 下注/加注无金额限制，最低下注额≥大盲注
    - 加注金额可自由选择，最低等于上一次加注额
    - 无加注次数限制
    - 全押：投入剩余所有筹码
    """

    @property
    def mode(self) -> BettingMode:
        return BettingMode.NO_LIMIT

    @property
    def max_raises_per_round(self) -> int:
        return 0  # 无限制

    def get_min_bet(self, big_blind: int, stage: GameStage) -> int:
        """最小下注额 = 大盲注"""
        return big_blind

    def get_min_raise(self, big_blind: int, stage: GameStage, last_raise_amount: int) -> int:
        """
        最小加注额 = 上次加注增量，最少为大盲注

        例：如果上次从100加到250（增量150），
        则本次最少要加150，加注到至少400
        """
        return max(big_blind, last_raise_amount)

    def get_max_raise(
        self,
        player: 'Player',
        current_bet: int,
        pot_total: int,
        big_blind: int,
        stage: GameStage
    ) -> int:
        """最大加注额 = 玩家全部筹码（减去跟注所需）"""
        to_call = max(0, current_bet - player.current_bet)
        return max(0, player.chips - to_call)


class LimitRule(BettingRule):
    """
    限注规则

    - 下注/加注金额固定
    - 前两轮（翻牌前+翻牌）用小注，后两轮（转牌+河牌）用大注
    - 小注 = 大盲注，大注 = 大盲注 × 2
    - 每轮最多3-4次加注（初始下注 + 2-3次再加注）
    """

    # 限注模式每轮最大加注次数（含首次下注）
    MAX_RAISES = 4

    @property
    def mode(self) -> BettingMode:
        return BettingMode.LIMIT

    @property
    def max_raises_per_round(self) -> int:
        return self.MAX_RAISES

    def _get_bet_increment(self, big_blind: int, stage: GameStage) -> int:
        """获取固定的下注增量"""
        if stage in [GameStage.PREFLOP, GameStage.FLOP]:
            return big_blind  # 小注
        else:
            return big_blind * 2  # 大注

    def get_min_bet(self, big_blind: int, stage: GameStage) -> int:
        """最小下注额 = 固定增量"""
        return self._get_bet_increment(big_blind, stage)

    def get_min_raise(self, big_blind: int, stage: GameStage, last_raise_amount: int) -> int:
        """最小加注额 = 固定增量"""
        return self._get_bet_increment(big_blind, stage)

    def get_max_raise(
        self,
        player: 'Player',
        current_bet: int,
        pot_total: int,
        big_blind: int,
        stage: GameStage
    ) -> int:
        """
        最大加注额 = 固定增量（限注模式下最小=最大）

        如果筹码不足固定增量，返回剩余筹码（相当于全押）
        """
        increment = self._get_bet_increment(big_blind, stage)
        to_call = max(0, current_bet - player.current_bet)
        available = player.chips - to_call

        if available <= 0:
            return 0

        return min(increment, available)


class PotLimitRule(BettingRule):
    """
    彩池限制规则

    - 最小下注额 ≥ 大盲注
    - 最大加注额 = 当前彩池大小
    - 无加注次数限制

    彩池限制加注额计算逻辑：
    当前可加注上限 = 底池现有金额 + 跟注金额 + 跟注金额
    （即：如果你要加注，先计算跟注后的底池，然后最多可以加这么多）
    """

    @property
    def mode(self) -> BettingMode:
        return BettingMode.POT_LIMIT

    @property
    def max_raises_per_round(self) -> int:
        return 0  # 无限制

    def get_min_bet(self, big_blind: int, stage: GameStage) -> int:
        """最小下注额 = 大盲注"""
        return big_blind

    def get_min_raise(self, big_blind: int, stage: GameStage, last_raise_amount: int) -> int:
        """最小加注额 = 大盲注或上次加注额"""
        return max(big_blind, last_raise_amount)

    def get_max_raise(
        self,
        player: 'Player',
        current_bet: int,
        pot_total: int,
        big_blind: int,
        stage: GameStage
    ) -> int:
        """
        最大加注额 = 当前彩池（跟注后）

        计算公式：
        1. 跟注金额 = current_bet - player.current_bet
        2. 跟注后底池 = pot_total + 跟注金额
        3. 最大加注额 = 跟注后底池

        例：底池100，当前下注50，你已下注20
        - 跟注金额 = 50 - 20 = 30
        - 跟注后底池 = 100 + 30 = 130
        - 最大加注额 = 130（你最终可下注到 50 + 130 = 180）
        """
        to_call = max(0, current_bet - player.current_bet)
        pot_after_call = pot_total + to_call
        max_raise = pot_after_call

        # 不能超过玩家筹码
        available = player.chips - to_call
        return min(max_raise, max(0, available))


class BettingRuleFactory:
    """下注规则工厂"""

    _rules = {
        BettingMode.NO_LIMIT: NoLimitRule,
        BettingMode.LIMIT: LimitRule,
        BettingMode.POT_LIMIT: PotLimitRule,
    }

    @classmethod
    def create(cls, mode: BettingMode) -> BettingRule:
        """创建下注规则实例"""
        rule_class = cls._rules.get(mode)
        if not rule_class:
            raise ValueError(f"Unsupported betting mode: {mode}")
        return rule_class()

    @classmethod
    def create_from_string(cls, mode_str: str) -> BettingRule:
        """根据字符串创建规则"""
        mode_map = {
            "no_limit": BettingMode.NO_LIMIT,
            "limit": BettingMode.LIMIT,
            "pot_limit": BettingMode.POT_LIMIT,
        }
        mode = mode_map.get(mode_str.lower())
        if not mode:
            raise ValueError(f"Unknown betting mode: {mode_str}")
        return cls.create(mode)
