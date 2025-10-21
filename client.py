"""WebSocket客户端 - 带有彩色终端UI"""
import asyncio
import json
from typing import Optional

import websockets
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text


class PokerClient:
    def __init__(self):
        self.console = Console()
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.client_id: Optional[str] = None
        self.room_id: Optional[str] = None
        self.player_name: Optional[str] = None
        self.game_state = None
        self.running = True

    def clear_screen(self):
        """清屏"""
        self.console.clear()

    def display_welcome(self):
        """显示欢迎界面"""
        self.clear_screen()
        welcome_text = Text()
        welcome_text.append("德州扑克 - 终端版\n", style="bold magenta")
        welcome_text.append("Texas Hold'em Poker", style="cyan")

        panel = Panel(
            Align.center(welcome_text),
            border_style="bright_blue",
            padding=(2, 4)
        )
        self.console.print(panel)

    def get_card_display(self, card_str: str) -> Text:
        """获取牌的彩色显示"""
        if card_str == "**":
            return Text("🂠", style="dim")

        # 解析花色和数字
        if len(card_str) < 2:
            return Text(card_str)

        rank = card_str[:-1]
        suit = card_str[-1]

        # 红色花色
        if suit in ['♥', '♦']:
            return Text(f"{rank}{suit}", style="bold red")
        # 黑色花色
        else:
            return Text(f"{rank}{suit}", style="bold white")

    def display_game_state(self):
        """显示游戏状态"""
        if not self.game_state:
            return

        self.clear_screen()

        # 创建布局
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=12)
        )

        # 头部 - 房间信息
        header_text = Text()
        header_text.append(f"房间: {self.room_id} | ", style="cyan")
        header_text.append(f"模式: {self.game_state.get('betting_mode', 'N/A')} | ", style="yellow")
        header_text.append(f"阶段: {self.game_state.get('stage', 'N/A')} | ", style="green")
        header_text.append(f"底池: ${self.game_state.get('pot', 0)}", style="bold magenta")

        layout["header"].update(Panel(header_text, border_style="blue"))

        # 主区域 - 公共牌和玩家信息
        main_content = Table.grid(padding=1)
        main_content.add_column(justify="center")

        # 公共牌
        community_cards = self.game_state.get('community_cards', [])
        if community_cards:
            cards_text = Text("公共牌: ", style="bold yellow")
            for card in community_cards:
                cards_text.append_text(self.get_card_display(card))
                cards_text.append(" ")
            main_content.add_row(cards_text)
        else:
            main_content.add_row(Text("等待发牌...", style="dim"))

        main_content.add_row("")

        # 玩家列表
        players_table = Table(show_header=True, header_style="bold cyan", border_style="blue")
        players_table.add_column("位置", justify="center", style="cyan", width=6)
        players_table.add_column("玩家", style="white", width=15)
        players_table.add_column("筹码", justify="right", style="yellow", width=10)
        players_table.add_column("当前注", justify="right", style="magenta", width=10)
        players_table.add_column("状态", justify="center", style="green", width=10)
        players_table.add_column("手牌", justify="center", width=15)

        players = self.game_state.get('players', [])
        dealer_pos = self.game_state.get('dealer_position', 0)
        current_player_idx = self.game_state.get('current_player_index', -1)

        for i, player in enumerate(players):
            position_text = ""
            if i == dealer_pos:
                position_text = "🎯 D"
            elif i == (dealer_pos + 1) % len(players):
                position_text = "SB"
            elif i == (dealer_pos + 2) % len(players):
                position_text = "BB"
            else:
                position_text = str(i)

            # 当前回合玩家高亮
            name_style = "bold green" if i == current_player_idx else "white"
            if player['id'] == self.client_id:
                name_style = "bold cyan"

            name = player['name']
            if player['id'] == self.client_id:
                name = f"👤 {name}"

            status = ""
            if player['folded']:
                status = "已弃牌"
            elif player['all_in']:
                status = "全押"
            else:
                status = "游戏中"

            # 手牌显示
            hand_text = Text()
            for card in player.get('hand', []):
                hand_text.append_text(self.get_card_display(card))
                hand_text.append(" ")

            players_table.add_row(
                position_text,
                name,
                f"${player['chips']}",
                f"${player['current_bet']}",
                status,
                hand_text
            )

        main_content.add_row(players_table)
        layout["main"].update(Panel(main_content, title="游戏桌", border_style="green"))

        # 底部 - 操作提示
        footer_content = ""
        if self.game_state.get('your_turn', False):
            footer_content = self._get_action_menu()
        else:
            footer_content = Text("等待其他玩家行动...", style="dim italic", justify="center")

        layout["footer"].update(Panel(footer_content, title="操作", border_style="yellow"))

        self.console.print(layout)

    def _get_action_menu(self) -> str:
        """获取操作菜单"""
        current_bet = self.game_state.get('current_bet', 0)
        min_raise = self.game_state.get('min_raise', 0)

        # 找到自己的信息
        my_player = None
        for player in self.game_state.get('players', []):
            if player['id'] == self.client_id:
                my_player = player
                break

        if not my_player:
            return ""

        my_bet = my_player['current_bet']
        my_chips = my_player['chips']
        to_call = current_bet - my_bet

        menu = Text()
        menu.append("可用操作:\n", style="bold yellow")
        menu.append("1. ", style="white")
        menu.append("弃牌 (Fold)\n", style="red")

        if to_call == 0:
            menu.append("2. ", style="white")
            menu.append("过牌 (Check)\n", style="green")
        else:
            menu.append("2. ", style="white")
            menu.append(f"跟注 (Call ${to_call})\n", style="green")

        if my_chips > to_call:
            menu.append("3. ", style="white")
            menu.append(f"加注 (Raise, 最小 ${min_raise})\n", style="cyan")

        menu.append("4. ", style="white")
        menu.append(f"全押 (All-in ${my_chips})\n", style="bold magenta")

        return menu

    async def connect(self, host: str, port: int):
        """连接到服务器"""
        try:
            uri = f"ws://{host}:{port}"
            self.console.print(f"正在连接到服务器 {uri}...", style="yellow")
            self.ws = await websockets.connect(uri)
            self.console.print("✓ 已连接到服务器", style="green")
            return True
        except Exception as e:
            self.console.print(f"✗ 连接失败: {e}", style="red")
            return False

    async def receive_messages(self):
        """接收服务器消息"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self.handle_server_message(data)
        except websockets.exceptions.ConnectionClosed:
            self.console.print("\n连接已断开", style="red")
            self.running = False
        except Exception as e:
            self.console.print(f"\n接收消息错误: {e}", style="red")
            self.running = False

    async def handle_server_message(self, data: dict):
        """处理服务器消息"""
        msg_type = data.get('type')

        if msg_type == 'connected':
            self.client_id = data['client_id']

        elif msg_type == 'room_created':
            self.room_id = data['room_id']
            self.player_name = data['player_name']
            self.console.print(f"\n✓ 房间已创建: {self.room_id}", style="green")
            self.console.print(f"其他玩家可以使用此房间ID加入游戏", style="cyan")

        elif msg_type == 'joined_room':
            self.room_id = data['room_id']
            self.player_name = data['player_name']
            self.console.print(f"\n✓ 已加入房间: {self.room_id}", style="green")

        elif msg_type == 'game_state':
            self.game_state = data
            self.display_game_state()

        elif msg_type == 'game_started':
            self.console.print(f"\n{data['message']}", style="bold green")

        elif msg_type == 'showdown':
            self.display_showdown(data)

        elif msg_type == 'error':
            self.console.print(f"\n✗ 错误: {data['message']}", style="red")

        elif msg_type == 'rooms_list':
            self.display_rooms_list(data['rooms'])

    def display_showdown(self, data: dict):
        """显示摊牌结果"""
        self.console.print("\n" + "="*50, style="yellow")
        self.console.print("摊牌结果", style="bold yellow", justify="center")
        self.console.print("="*50 + "\n", style="yellow")

        winners = data.get('winners', [])
        for winner in winners:
            winner_text = Text()
            winner_text.append("🏆 ", style="yellow")
            winner_text.append(f"{winner['player_name']} ", style="bold green")
            winner_text.append(f"赢得 ${winner['amount']} ", style="bold magenta")
            winner_text.append(f"({winner['hand_name']})", style="cyan")

            if 'hand' in winner:
                winner_text.append("\n   手牌: ", style="white")
                for card in winner['hand']:
                    winner_text.append_text(self.get_card_display(card))
                    winner_text.append(" ")

            self.console.print(Panel(winner_text, border_style="yellow"))

        self.console.print("\n按回车继续...", style="dim")

    def display_rooms_list(self, rooms: list):
        """显示房间列表"""
        self.clear_screen()

        if not rooms:
            self.console.print("当前没有可用的房间", style="yellow")
            return

        table = Table(title="可用房间", show_header=True, header_style="bold cyan")
        table.add_column("房间ID", style="cyan")
        table.add_column("玩家数", justify="center", style="yellow")
        table.add_column("状态", style="green")
        table.add_column("模式", style="magenta")

        for room in rooms:
            table.add_row(
                room['room_id'],
                str(room['players']),
                room['status'],
                room['betting_mode']
            )

        self.console.print(table)

    async def send_message(self, message: dict):
        """发送消息到服务器"""
        if self.ws:
            await self.ws.send(json.dumps(message))

    async def main_menu(self):
        """主菜单"""
        self.display_welcome()

        self.console.print("\n请选择操作:", style="bold cyan")
        self.console.print("1. 创建房间")
        self.console.print("2. 加入房间")
        self.console.print("3. 查看房间列表")
        self.console.print("4. 退出")

        choice = Prompt.ask("\n请输入选项", choices=["1", "2", "3", "4"])

        if choice == "1":
            await self.create_room_flow()
        elif choice == "2":
            await self.join_room_flow()
        elif choice == "3":
            await self.list_rooms_flow()
        elif choice == "4":
            self.running = False
            return

    async def create_room_flow(self):
        """创建房间流程"""
        self.player_name = Prompt.ask("请输入你的昵称", default="玩家")

        self.console.print("\n选择下注模式:", style="bold cyan")
        self.console.print("1. 限注 (Limit)")
        self.console.print("2. 无限注 (No Limit)")
        self.console.print("3. 彩池限注 (Pot Limit)")

        mode_choice = Prompt.ask("请选择模式", choices=["1", "2", "3"], default="1")

        betting_mode = "LIMIT"
        if mode_choice == "2":
            betting_mode = "NO_LIMIT"
        elif mode_choice == "3":
            betting_mode = "POT_LIMIT"

        await self.send_message({
            'type': 'create_room',
            'player_name': self.player_name,
            'betting_mode': betting_mode
        })

        # 等待响应
        await asyncio.sleep(1)

        # 进入游戏循环
        await self.game_loop()

    async def join_room_flow(self):
        """加入房间流程"""
        self.player_name = Prompt.ask("请输入你的昵称", default="玩家")
        room_id = Prompt.ask("请输入房间ID")

        await self.send_message({
            'type': 'join_room',
            'room_id': room_id,
            'player_name': self.player_name
        })

        # 等待响应
        await asyncio.sleep(1)

        # 进入游戏循环
        await self.game_loop()

    async def list_rooms_flow(self):
        """查看房间列表"""
        await self.send_message({'type': 'list_rooms'})
        await asyncio.sleep(1)
        input("\n按回车返回主菜单...")

    async def game_loop(self):
        """游戏循环"""
        while self.running and self.room_id:
            # 检查是否是房主并且在等待状态
            if (self.game_state and
                self.game_state.get('room_owner') == self.client_id and
                self.game_state.get('stage') == '等待开始'):

                if len(self.game_state.get('players', [])) >= 2:
                    start = Prompt.ask("\n是否开始游戏? (y/n)", choices=["y", "n"])
                    if start == "y":
                        await self.send_message({'type': 'start_game'})
                        await asyncio.sleep(0.5)
                        continue

            # 检查是否轮到自己
            if self.game_state and self.game_state.get('your_turn', False):
                action = await self.get_player_action()
                if action:
                    await self.send_message({
                        'type': 'player_action',
                        **action
                    })
                    await asyncio.sleep(0.5)
            else:
                # 等待一段时间
                await asyncio.sleep(1)

            # 检查是否要离开
            # 这里可以添加额外的退出逻辑

    async def get_player_action(self) -> Optional[dict]:
        """获取玩家操作"""
        try:
            choice = Prompt.ask("\n请选择操作 (1-4)", choices=["1", "2", "3", "4"])

            current_bet = self.game_state.get('current_bet', 0)
            my_player = next((p for p in self.game_state.get('players', []) if p['id'] == self.client_id), None)

            if not my_player:
                return None

            my_bet = my_player['current_bet']
            to_call = current_bet - my_bet

            if choice == "1":
                return {'action': 'fold'}
            elif choice == "2":
                if to_call == 0:
                    return {'action': 'check'}
                else:
                    return {'action': 'call'}
            elif choice == "3":
                min_raise = self.game_state.get('min_raise', 0)
                raise_amount = int(Prompt.ask(f"请输入加注额 (最小 {min_raise})"))
                return {'action': 'raise', 'amount': raise_amount}
            elif choice == "4":
                return {'action': 'raise', 'amount': my_player['chips']}

        except KeyboardInterrupt:
            self.running = False
            return None

    async def run(self, host: str, port: int):
        """运行客户端"""
        if not await self.connect(host, port):
            return

        # 创建接收消息的任务
        receive_task = asyncio.create_task(self.receive_messages())

        try:
            while self.running:
                await self.main_menu()

        except KeyboardInterrupt:
            self.console.print("\n正在退出...", style="yellow")
        finally:
            if self.room_id and self.ws:
                try:
                    await self.send_message({'type': 'leave_room'})
                except:
                    pass
            receive_task.cancel()
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description='德州扑克客户端')
    parser.add_argument('--host', default='localhost', help='服务器地址')
    parser.add_argument('--port', type=int, default=8765, help='服务器端口')

    args = parser.parse_args()

    client = PokerClient()
    try:
        asyncio.run(client.run(args.host, args.port))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
