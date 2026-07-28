import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.services.auth import get_user_by_id
from app.services.event_bus import event_bus


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def _validate_token(websocket: WebSocket) -> bool:
    """Validate the JWT token from the query parameter."""
    token = websocket.query_params.get("token")
    if not token:
        return False

    try:
        payload = decode_token(token)
    except ValueError:
        return False

    if payload.get("type") != "access":
        return False

    user_id = payload.get("sub")
    if not user_id:
        return False

    db = SessionLocal()
    try:
        user = get_user_by_id(db, user_id)
        if user is None or not user.is_active:
            return False
    finally:
        db.close()

    return True


@router.websocket("/kafka/events")
async def kafka_events_websocket(websocket: WebSocket) -> None:
    await websocket.accept()

    if not await _validate_token(websocket):
        await websocket.send_json({"error": "Unauthorized: invalid or missing token"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await event_bus.subscribe(websocket)
    try:
        # Keep the connection alive; messages are pushed via event_bus.publish
        while True:
            # Wait for the client to send a ping or disconnect
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception:
        logger.exception("WebSocket error.")
    finally:
        await event_bus.unsubscribe(websocket)