"""WebSocket连接管理器"""
from typing import Dict, Any
from fastapi import WebSocket


class ConnectionManager:
    """WebSocket连接管理"""

    def __init__(self):
        # room_id -> {player_id -> websocket}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, room_id: str, player_id: str, websocket: WebSocket):
        """添加连接"""
        await websocket.accept()
        if room_id not in self.connections:
            self.connections[room_id] = {}
        self.connections[room_id][player_id] = websocket

    def disconnect(self, room_id: str, player_id: str):
        """移除连接"""
        if room_id in self.connections:
            self.connections[room_id].pop(player_id, None)
            if not self.connections[room_id]:
                del self.connections[room_id]

    def get_room_connections(self, room_id: str) -> Dict[str, WebSocket]:
        """获取房间所有连接"""
        return self.connections.get(room_id, {})

    def get_player_connection(self, room_id: str, player_id: str) -> WebSocket:
        """获取玩家连接"""
        if room_id in self.connections:
            return self.connections[room_id].get(player_id)
        return None

    async def broadcast_to_room(self, room_id: str, message: dict):
        """广播消息到房间所有玩家"""
        connections = self.get_room_connections(room_id)
        for websocket in connections.values():
            try:
                await websocket.send_json(message)
            except Exception:
                pass

    async def send_to_player(self, room_id: str, player_id: str, message: dict):
        """发送消息给指定玩家"""
        websocket = self.get_player_connection(room_id, player_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception:
                pass

    async def send_personal_state(
        self,
        room_id: str,
        get_state_func,
        additional_data: dict = None
    ):
        """向房间内每个玩家发送个人视角的状态"""
        connections = self.get_room_connections(room_id)
        for player_id, websocket in connections.items():
            try:
                state = get_state_func(player_id)
                if state:
                    message = {"type": "game_state", "data": state}
                    if additional_data:
                        message["data"].update(additional_data)
                    await websocket.send_json(message)
            except Exception:
                pass

    def is_connected(self, room_id: str, player_id: str) -> bool:
        """检查玩家是否已连接"""
        return (
            room_id in self.connections and
            player_id in self.connections[room_id]
        )

    def get_room_player_count(self, room_id: str) -> int:
        """获取房间连接数"""
        return len(self.connections.get(room_id, {}))
