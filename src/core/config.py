"""配置"""
from dataclasses import dataclass


@dataclass
class Settings:
    """应用配置"""
    # 服务器
    host: str = "0.0.0.0"
    port: int = 8080

    # 游戏默认配置
    default_chips: int = 1000
    default_small_blind: int = 10
    default_big_blind: int = 20
    max_players_per_room: int = 10

    # 计时器
    turn_timeout: int = 30  # 每回合超时秒数

    # 聊天
    max_chat_history: int = 100
    max_action_history: int = 50


settings = Settings()
