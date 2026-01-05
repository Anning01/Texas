"""依赖注入"""
from functools import lru_cache
from src.infrastructure.communication import ConnectionManager
from src.infrastructure.storage import MemoryRoomStorage


# 单例实例
_connection_manager = None
_room_storage = None


def get_connection_manager() -> ConnectionManager:
    """获取连接管理器单例"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def get_room_storage() -> MemoryRoomStorage:
    """获取房间存储单例"""
    global _room_storage
    if _room_storage is None:
        _room_storage = MemoryRoomStorage()
    return _room_storage


def get_game_service():
    """获取游戏服务"""
    from src.application.services.game_service import GameService
    return GameService(
        room_storage=get_room_storage(),
        connection_manager=get_connection_manager()
    )
