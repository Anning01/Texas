"""WebSocket服务器"""
import asyncio
import json
import websockets
from typing import Dict, Set
from poker_game import GameState, BettingMode, GameStage
import uuid


class PokerServer:
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.rooms: Dict[str, GameState] = {}
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.client_rooms: Dict[str, str] = {}  # client_id -> room_id

    async def handle_client(self, websocket):
        """处理客户端连接"""
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket

        try:
            await websocket.send(json.dumps({
                'type': 'connected',
                'client_id': client_id
            }))

            async for message in websocket:
                await self.handle_message(client_id, message)

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.disconnect_client(client_id)

    async def handle_message(self, client_id: str, message: str):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'create_room':
                await self.create_room(client_id, data)
            elif msg_type == 'join_room':
                await self.join_room(client_id, data)
            elif msg_type == 'leave_room':
                await self.leave_room(client_id)
            elif msg_type == 'start_game':
                await self.start_game(client_id, data)
            elif msg_type == 'player_action':
                await self.player_action(client_id, data)
            elif msg_type == 'list_rooms':
                await self.list_rooms(client_id)

        except Exception as e:
            await self.send_error(client_id, str(e))

    async def create_room(self, client_id: str, data: dict):
        """创建房间"""
        room_id = str(uuid.uuid4())[:8]
        player_name = data.get('player_name', f'Player_{client_id[:6]}')
        betting_mode_str = data.get('betting_mode', 'LIMIT')

        # 转换下注模式
        betting_mode = BettingMode.LIMIT
        if betting_mode_str == 'NO_LIMIT':
            betting_mode = BettingMode.NO_LIMIT
        elif betting_mode_str == 'POT_LIMIT':
            betting_mode = BettingMode.POT_LIMIT

        game_state = GameState(betting_mode=betting_mode)
        game_state.add_player(client_id, player_name)
        self.rooms[room_id] = game_state
        self.client_rooms[client_id] = room_id

        await self.send_to_client(client_id, {
            'type': 'room_created',
            'room_id': room_id,
            'player_name': player_name,
            'betting_mode': betting_mode.value
        })

        await self.broadcast_room_state(room_id)

    async def join_room(self, client_id: str, data: dict):
        """加入房间"""
        room_id = data.get('room_id')
        player_name = data.get('player_name', f'Player_{client_id[:6]}')

        if room_id not in self.rooms:
            await self.send_error(client_id, '房间不存在')
            return

        game_state = self.rooms[room_id]

        if game_state.stage != GameStage.WAITING:
            await self.send_error(client_id, '游戏已开始,无法加入')
            return

        if len(game_state.players) >= 9:
            await self.send_error(client_id, '房间已满')
            return

        game_state.add_player(client_id, player_name)
        self.client_rooms[client_id] = room_id

        await self.send_to_client(client_id, {
            'type': 'joined_room',
            'room_id': room_id,
            'player_name': player_name
        })

        await self.broadcast_room_state(room_id)

    async def leave_room(self, client_id: str):
        """离开房间"""
        if client_id not in self.client_rooms:
            return

        room_id = self.client_rooms[client_id]
        game_state = self.rooms.get(room_id)

        if game_state:
            # 如果游戏正在进行中,将玩家标记为弃牌而不是移除
            if game_state.stage not in [GameStage.WAITING, GameStage.ENDED]:
                player = next((p for p in game_state.players if p.id == client_id), None)
                if player:
                    player.folded = True
                    # 如果轮到该玩家,跳到下一个玩家
                    if (game_state.current_player_index < len(game_state.players) and
                        game_state.players[game_state.current_player_index].id == client_id):
                        game_state.current_player_index = game_state.get_next_active_player_index(
                            game_state.current_player_index
                        )
            else:
                # 游戏未开始,直接移除玩家
                game_state.remove_player(client_id)

            # 如果房间空了,删除房间
            if len(game_state.players) == 0:
                del self.rooms[room_id]
            else:
                # 如果房主离开,转移房主
                if game_state.room_owner == client_id and len(game_state.players) > 0:
                    game_state.room_owner = game_state.players[0].id

                # 修正 current_player_index 如果越界
                if game_state.current_player_index >= len(game_state.players):
                    game_state.current_player_index = 0

                await self.broadcast_room_state(room_id)

        del self.client_rooms[client_id]

    async def start_game(self, client_id: str, data: dict):
        """开始游戏"""
        if client_id not in self.client_rooms:
            await self.send_error(client_id, '你不在任何房间')
            return

        room_id = self.client_rooms[client_id]
        game_state = self.rooms[room_id]

        if game_state.room_owner != client_id:
            await self.send_error(client_id, '只有房主可以开始游戏')
            return

        if len(game_state.players) < 2:
            await self.send_error(client_id, '至少需要2名玩家')
            return

        if game_state.start_new_hand():
            await self.broadcast_room_state(room_id)
            await self.broadcast_to_room(room_id, {
                'type': 'game_started',
                'message': '游戏开始!'
            })

    async def player_action(self, client_id: str, data: dict):
        """玩家行动"""
        if client_id not in self.client_rooms:
            await self.send_error(client_id, '你不在任何房间')
            return

        room_id = self.client_rooms[client_id]
        game_state = self.rooms[room_id]

        if game_state.stage == GameStage.WAITING:
            await self.send_error(client_id, '游戏未开始')
            return

        current_player = game_state.players[game_state.current_player_index]
        if current_player.id != client_id:
            await self.send_error(client_id, '不是你的回合')
            return

        action = data.get('action')
        amount = data.get('amount', 0)

        # 执行动作
        if action == 'fold':
            current_player.folded = True
        elif action == 'check':
            if current_player.current_bet < game_state.current_bet:
                await self.send_error(client_id, '无法过牌,需要跟注或加注')
                return
        elif action == 'call':
            call_amount = game_state.current_bet - current_player.current_bet
            call_amount = min(call_amount, current_player.chips)
            current_player.chips -= call_amount
            current_player.current_bet += call_amount
            current_player.total_bet += call_amount
            game_state.main_pot += call_amount

            if current_player.chips == 0:
                current_player.all_in = True
        elif action == 'raise':
            # 计算加注金额
            call_amount = game_state.current_bet - current_player.current_bet
            total_amount = call_amount + amount

            # 检查加注是否合法
            if amount < game_state.min_raise and current_player.chips > total_amount:
                await self.send_error(client_id, f'最小加注额为 {game_state.min_raise}')
                return

            # 根据不同模式检查
            if game_state.betting_mode == BettingMode.LIMIT:
                # 限注模式,每轮固定加注额
                if amount != game_state.big_blind:
                    await self.send_error(client_id, f'限注模式下每次加注 {game_state.big_blind}')
                    return
            elif game_state.betting_mode == BettingMode.POT_LIMIT:
                # 彩池限注,不能超过当前彩池大小
                max_raise = game_state.main_pot + call_amount
                if amount > max_raise:
                    await self.send_error(client_id, f'彩池限注模式下最大加注 {max_raise}')
                    return

            total_amount = min(total_amount, current_player.chips)
            current_player.chips -= total_amount
            current_player.current_bet += total_amount
            current_player.total_bet += total_amount
            game_state.main_pot += total_amount
            game_state.current_bet = current_player.current_bet
            game_state.min_raise = amount
            game_state.last_raiser_index = game_state.current_player_index

            if current_player.chips == 0:
                current_player.all_in = True

        # 检查下注轮是否结束
        if game_state.is_betting_round_complete():
            active_players = game_state.get_active_players()
            if len(active_players) == 1:
                # 只剩一个玩家,直接赢
                game_state.stage = GameStage.SHOWDOWN
                winners = game_state.determine_winners()
                await self.broadcast_to_room(room_id, {
                    'type': 'showdown',
                    'winners': [{
                        'player_id': w[0].id,
                        'player_name': w[0].name,
                        'amount': w[1],
                        'hand_name': '对手弃牌'
                    } for w in winners]
                })
                game_state.end_hand()
            elif game_state.stage == GameStage.RIVER:
                # 河牌后进入摊牌
                game_state.stage = GameStage.SHOWDOWN
                winners = game_state.determine_winners()
                from poker_game import HandEvaluator
                await self.broadcast_to_room(room_id, {
                    'type': 'showdown',
                    'winners': [{
                        'player_id': w[0].id,
                        'player_name': w[0].name,
                        'amount': w[1],
                        'hand_name': HandEvaluator.get_hand_name(w[2]),
                        'hand': [str(card) for card in w[0].hand]
                    } for w in winners]
                })
                game_state.end_hand()
            else:
                # 进入下一阶段
                game_state.advance_stage()
        else:
            # 下一个玩家
            game_state.current_player_index = game_state.get_next_active_player_index(
                game_state.current_player_index
            )

        await self.broadcast_room_state(room_id)

    async def list_rooms(self, client_id: str):
        """列出所有房间"""
        rooms_info = []
        for room_id, game_state in self.rooms.items():
            rooms_info.append({
                'room_id': room_id,
                'players': len(game_state.players),
                'status': game_state.stage.value,
                'betting_mode': game_state.betting_mode.value
            })

        await self.send_to_client(client_id, {
            'type': 'rooms_list',
            'rooms': rooms_info
        })

    async def disconnect_client(self, client_id: str):
        """断开客户端"""
        await self.leave_room(client_id)
        if client_id in self.clients:
            del self.clients[client_id]

    async def broadcast_room_state(self, room_id: str):
        """广播房间状态给所有玩家"""
        if room_id not in self.rooms:
            return

        game_state = self.rooms[room_id]

        for player in game_state.players:
            await self.send_game_state(player.id, room_id)

    async def send_game_state(self, client_id: str, room_id: str):
        """发送游戏状态给特定玩家"""
        game_state = self.rooms[room_id]

        # 获取该玩家
        player = next((p for p in game_state.players if p.id == client_id), None)
        if not player:
            return

        # 构建玩家列表(隐藏其他玩家的底牌)
        players_info = []
        for p in game_state.players:
            player_info = {
                'id': p.id,
                'name': p.name,
                'chips': p.chips,
                'current_bet': p.current_bet,
                'folded': p.folded,
                'all_in': p.all_in,
                'position': p.position
            }
            # 只显示自己的底牌
            if p.id == client_id:
                player_info['hand'] = [str(card) for card in p.hand]
            else:
                player_info['hand'] = ['**', '**'] if len(p.hand) > 0 and not p.folded else []

            players_info.append(player_info)

        # 检查当前玩家索引是否有效
        your_turn = False
        if (game_state.stage not in [GameStage.WAITING, GameStage.SHOWDOWN] and
            0 <= game_state.current_player_index < len(game_state.players)):
            your_turn = game_state.players[game_state.current_player_index].id == client_id

        state_data = {
            'type': 'game_state',
            'stage': game_state.stage.value,
            'betting_mode': game_state.betting_mode.value,
            'pot': game_state.main_pot,
            'current_bet': game_state.current_bet,
            'min_raise': game_state.min_raise,
            'community_cards': [str(card) for card in game_state.community_cards],
            'players': players_info,
            'dealer_position': game_state.dealer_position,
            'current_player_index': game_state.current_player_index,
            'room_owner': game_state.room_owner,
            'your_turn': your_turn
        }

        await self.send_to_client(client_id, state_data)

    async def broadcast_to_room(self, room_id: str, message: dict):
        """向房间所有玩家广播消息"""
        if room_id not in self.rooms:
            return

        game_state = self.rooms[room_id]
        for player in game_state.players:
            await self.send_to_client(player.id, message)

    async def send_to_client(self, client_id: str, message: dict):
        """发送消息给客户端"""
        if client_id in self.clients:
            try:
                await self.clients[client_id].send(json.dumps(message))
            except:
                pass

    async def send_error(self, client_id: str, error_message: str):
        """发送错误消息"""
        await self.send_to_client(client_id, {
            'type': 'error',
            'message': error_message
        })

    async def start(self):
        """启动服务器"""
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"德州扑克服务器启动: ws://{self.host}:{self.port}")
            await asyncio.Future()  # 永久运行


def main():
    import argparse

    parser = argparse.ArgumentParser(description='德州扑克服务器')
    parser.add_argument('--host', default='0.0.0.0', help='服务器地址')
    parser.add_argument('--port', type=int, default=8765, help='服务器端口')

    args = parser.parse_args()

    server = PokerServer(host=args.host, port=args.port)
    asyncio.run(server.start())


if __name__ == '__main__':
    main()
