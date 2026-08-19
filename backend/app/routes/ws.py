from fastapi import APIRouter,WebSocket,WebSocketDisconnect
from ..websocket.manager import WebSocketManager
router=APIRouter()
manager=WebSocketManager()
@router.websocket("/ws/player")
async def ws_player(ws:WebSocket):
    await manager.connect(ws)
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: manager.disconnect(ws)
