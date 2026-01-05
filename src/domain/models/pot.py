"""底池模型"""
from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class SidePot:
    """边池"""
    amount: int
    eligible_player_ids: Set[str] = field(default_factory=set)


@dataclass
class Pot:
    """底池管理"""
    main_pot: int = 0
    side_pots: List[SidePot] = field(default_factory=list)

    def add(self, amount: int):
        """增加主池"""
        self.main_pot += amount

    @property
    def total(self) -> int:
        """总底池"""
        return self.main_pot + sum(sp.amount for sp in self.side_pots)

    def reset(self):
        """重置"""
        self.main_pot = 0
        self.side_pots = []
