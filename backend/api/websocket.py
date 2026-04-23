from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections
active_connections: Dict[str, Set[WebSocket]] = {}


async def send_processing_update(document_id: str, stage: str, data: dict = None):
    """Send a processing update to all clients subscribed to a document."""
    if document_id in active_connections:
        message = {
            "type": "processing_update",
            "document_id": document_id,
            "stage": stage,
            "data": data or {}
        }
        disconnected = set()
        for websocket in active_connections[document_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send update to websocket: {e}")
                disconnected.add(websocket)

        # Remove disconnected websockets
        active_connections[document_id] -= disconnected
        if not active_connections[document_id]:
            del active_connections[document_id]


@router.websocket("/document/{document_id}")
async def document_processing_websocket(websocket: WebSocket, document_id: str):
    """WebSocket endpoint for real-time document processing updates."""
    await websocket.accept()

    # Add to active connections
    if document_id not in active_connections:
        active_connections[document_id] = set()
    active_connections[document_id].add(websocket)

    try:
        while True:
            # Keep the connection alive and wait for client messages
            data = await websocket.receive_text()
            # For now, we don't expect client messages, but this keeps the connection open
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for document {document_id}")
    finally:
        # Remove from active connections
        if document_id in active_connections:
            active_connections[document_id].discard(websocket)
            if not active_connections[document_id]:
                del active_connections[document_id]