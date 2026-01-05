"""核心模块"""
from .config import Settings
from .dependencies import get_game_service, get_connection_manager

__all__ = ['Settings', 'get_game_service', 'get_connection_manager']
