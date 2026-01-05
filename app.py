"""FastAPI 德州扑克在线游戏 - 使用DDD架构"""
import uuid
from typing import Optional
from contextlib import asynccontextmanager
from urllib.parse import quote, unquote

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.domain.enums import BettingMode
from src.core.dependencies import get_game_service, get_connection_manager


# ============ FastAPI 应用 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    yield


app = FastAPI(title="德州扑克", lifespan=lifespan)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ============ 页面路由 ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, player_id: Optional[str] = Cookie(None)):
    """首页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "player_id": player_id
    })


@app.post("/set-player")
async def set_player(player_name: str = Form(...)):
    """设置玩家名称"""
    player_id = str(uuid.uuid4())
    # URL编码支持中文名
    encoded_name = quote(player_name, safe='')
    response = RedirectResponse(url="/lobby", status_code=303)
    response.set_cookie(key="player_id", value=player_id, max_age=86400)
    response.set_cookie(key="player_name", value=encoded_name, max_age=86400)
    return response


@app.get("/lobby", response_class=HTMLResponse)
async def lobby(
    request: Request,
    player_id: Optional[str] = Cookie(None),
    player_name: Optional[str] = Cookie(None)
):
    """大厅页面"""
    if not player_id or not player_name:
        return RedirectResponse(url="/")

    # 解码中文名
    decoded_name = unquote(player_name)
    game_service = get_game_service()
    rooms = game_service.get_room_list()
    return templates.TemplateResponse("lobby.html", {
        "request": request,
        "player_id": player_id,
        "player_name": decoded_name,
        "rooms": rooms
    })


@app.post("/create-room")
async def create_room(
    room_name: str = Form(...),
    betting_mode: str = Form("no_limit"),
    small_blind: int = Form(10),
    big_blind: int = Form(20),
    ante: int = Form(0),
    player_id: Optional[str] = Cookie(None),
    player_name: Optional[str] = Cookie(None)
):
    """创建房间"""
    if not player_id or not player_name:
        return RedirectResponse(url="/")

    # 解码中文名
    decoded_name = unquote(player_name)

    mode_map = {
        "limit": BettingMode.LIMIT,
        "no_limit": BettingMode.NO_LIMIT,
        "pot_limit": BettingMode.POT_LIMIT
    }
    mode = mode_map.get(betting_mode, BettingMode.NO_LIMIT)

    # 验证盲注参数
    small_blind = max(1, small_blind)
    big_blind = max(small_blind * 2, big_blind)
    ante = max(0, ante)

    game_service = get_game_service()
    table = game_service.create_room(room_name, mode, small_blind, big_blind, ante)
    game_service.join_room(table.room_id, player_id, decoded_name)

    return RedirectResponse(url=f"/room/{table.room_id}", status_code=303)


@app.get("/room/{room_id}", response_class=HTMLResponse)
async def game_room(
    request: Request,
    room_id: str,
    player_id: Optional[str] = Cookie(None),
    player_name: Optional[str] = Cookie(None)
):
    """游戏房间页面"""
    if not player_id or not player_name:
        return RedirectResponse(url="/")

    # 解码中文名
    decoded_name = unquote(player_name)

    game_service = get_game_service()
    table = game_service.get_room(room_id)
    if not table:
        return RedirectResponse(url="/lobby")

    # 加入房间
    game_service.join_room(room_id, player_id, decoded_name)

    return templates.TemplateResponse("game.html", {
        "request": request,
        "room_id": room_id,
        "player_id": player_id,
        "player_name": decoded_name,
        "room_name": table.room_name
    })


@app.post("/leave-room/{room_id}")
async def leave_room(
    room_id: str,
    player_id: Optional[str] = Cookie(None)
):
    """离开房间"""
    if player_id:
        game_service = get_game_service()
        game_service.leave_room(room_id, player_id)
    return RedirectResponse(url="/lobby", status_code=303)


# ============ WebSocket ============

@app.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    """WebSocket 连接"""
    game_service = get_game_service()
    connection_manager = get_connection_manager()

    table = game_service.get_room(room_id)
    if not table:
        await websocket.close()
        return

    await connection_manager.connect(room_id, player_id, websocket)

    try:
        # 发送初始状态
        state = game_service.get_game_state_for_player(room_id, player_id)
        if state:
            await websocket.send_json({"type": "game_state", "data": state})

        # 广播玩家加入
        await game_service.broadcast_game_state(room_id)

        # 接收消息
        while True:
            data = await websocket.receive_json()
            await game_service.handle_player_action(room_id, player_id, data)

    except WebSocketDisconnect:
        connection_manager.disconnect(room_id, player_id)
        await game_service.broadcast_game_state(room_id)


# ============ API 接口 ============

@app.get("/api/rooms")
async def api_rooms():
    """获取房间列表 API"""
    game_service = get_game_service()
    return game_service.get_room_list()


@app.get("/api/room/{room_id}/state")
async def api_room_state(room_id: str, player_id: Optional[str] = Cookie(None)):
    """获取房间状态 API"""
    if not player_id:
        return {"error": "未登录"}
    game_service = get_game_service()
    state = game_service.get_game_state_for_player(room_id, player_id)
    if not state:
        return {"error": "房间不存在"}
    return state


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
