"""
Real-time WebSocket connection manager for GATI ICCC Operator Dashboards.

Supports three subscription modes:
  1. Global broadcast  — all connected clients receive every update.
  2. Per-junction room — client subscribes to a specific junction_id;
     only that junction's state updates are pushed to it.
  3. Alerts room       — receives HIGH/CRITICAL incidents and anomalies
     from any junction.

Adding a new junction adds a new room automatically; no code change needed.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger("central.ws_manager")


class WebSocketManager:
    """
    Manages active operator WebSocket connections with per-junction subscription rooms.
    Thread-safety: all mutations happen in the async event loop; no explicit locks needed.
    """

    def __init__(self):
        # Global connections (receive every update)
        self._global: List[WebSocket] = []
        # Per-junction rooms: junction_id → set of WebSocket connections
        self._junction_rooms: Dict[str, List[WebSocket]] = defaultdict(list)
        # Alerts room: receives HIGH/CRITICAL incidents from any junction
        self._alert_subscribers: List[WebSocket] = []

    # ── Connection lifecycle ──────────────────────────────────────────────

    async def connect_global(self, websocket: WebSocket):
        """Accept connection and add to global broadcast list."""
        await websocket.accept()
        self._global.append(websocket)
        logger.debug(f"[WS] Global connection opened. Total global: {len(self._global)}")

    async def connect_junction(self, websocket: WebSocket, junction_id: str):
        """Accept connection and subscribe to a specific junction room."""
        await websocket.accept()
        self._junction_rooms[junction_id].append(websocket)
        logger.debug(f"[WS] Junction '{junction_id}' connection. Room size: {len(self._junction_rooms[junction_id])}")

    async def connect_alerts(self, websocket: WebSocket):
        """Accept connection and subscribe to the high-priority alerts stream."""
        await websocket.accept()
        self._alert_subscribers.append(websocket)
        logger.debug(f"[WS] Alerts subscriber connected. Total: {len(self._alert_subscribers)}")

    def disconnect(self, websocket: WebSocket, junction_id: Optional[str] = None):
        """Remove websocket from all lists it was registered in."""
        if websocket in self._global:
            self._global.remove(websocket)
        if websocket in self._alert_subscribers:
            self._alert_subscribers.remove(websocket)
        if junction_id and websocket in self._junction_rooms.get(junction_id, []):
            self._junction_rooms[junction_id].remove(websocket)
        # Sweep all junction rooms as fallback
        for room_list in self._junction_rooms.values():
            if websocket in room_list:
                room_list.remove(websocket)

    # ── Broadcasting ──────────────────────────────────────────────────────

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast to all globally connected clients."""
        await self._send_to_list(self._global, message)

    async def broadcast_junction(self, junction_id: str, message: Dict[str, Any]):
        """
        Broadcast to global subscribers AND junction-specific room subscribers.
        Global subscribers always get everything (dashboard shows all junctions).
        """
        targets = list(self._global) + list(self._junction_rooms.get(junction_id, []))
        await self._send_to_list(targets, message)

    async def broadcast_alerts(self, message: Dict[str, Any]):
        """Broadcast to alerts room AND global subscribers."""
        targets = list(self._alert_subscribers) + list(self._global)
        await self._send_to_list(targets, message)

    @staticmethod
    async def _send_to_list(connections: List[WebSocket], message: Dict[str, Any]):
        """Send JSON message to a list of connections, pruning dead ones."""
        dead: List[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            for room_list in [connections]:
                if ws in room_list:
                    room_list.remove(ws)

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "global_connections": len(self._global),
            "alert_subscribers": len(self._alert_subscribers),
            "junction_rooms": {jid: len(lst) for jid, lst in self._junction_rooms.items() if lst},
        }
