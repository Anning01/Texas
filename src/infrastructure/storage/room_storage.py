"""房间存储"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from src.domain.models.poker_table import PokerTable


class RoomStorage(ABC):
    """房间存储抽象接口"""

    @abstractmethod
    def save(self, table: PokerTable) -> None:
        """保存房间"""
        pass

    @abstractmethod
    def get(self, room_id: str) -> Optional[PokerTable]:
        """获取房间"""
        pass

    @abstractmethod
    def delete(self, room_id: str) -> None:
        """删除房间"""
        pass

    @abstractmethod
    def list_all(self) -> List[PokerTable]:
        """列出所有房间"""
        pass

    @abstractmethod
    def exists(self, room_id: str) -> bool:
        """检查房间是否存在"""
        pass


class MemoryRoomStorage(RoomStorage):
    """内存房间存储实现"""

    def __init__(self):
        self._rooms: Dict[str, PokerTable] = {}

    def save(self, table: PokerTable) -> None:
        """保存房间"""
        self._rooms[table.room_id] = table

    def get(self, room_id: str) -> Optional[PokerTable]:
        """获取房间"""
        return self._rooms.get(room_id)

    def delete(self, room_id: str) -> None:
        """删除房间"""
        self._rooms.pop(room_id, None)

    def list_all(self) -> List[PokerTable]:
        """列出所有房间"""
        return list(self._rooms.values())

    def exists(self, room_id: str) -> bool:
        """检查房间是否存在"""
        return room_id in self._rooms

    def get_room_count(self) -> int:
        """获取房间数量"""
        return len(self._rooms)
