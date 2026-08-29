from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.event_bus import manager

router = APIRouter(prefix="/ws", tags=["Realtime"])


@router.websocket("/orders")
async def websocket_orders_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time order stream updates.
    The frontend command center connects to this endpoint to receive live status changes.
    """
    await manager.connect(websocket)
    try:
        # Send initial connected greeting
        await websocket.send_json({"type": "CONNECTED", "message": "Subscribed to live order mesh stream"})
        while True:
            # Keep-alive loop
            data = await websocket.receive_text()
            # Echo ping-pong if needed
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
