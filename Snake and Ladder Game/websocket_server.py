#!/usr/bin/env python3
"""
Clean WebSocket Server for Snake & Ladder multiplayer
Handles session management and message relay between players
"""

import asyncio
import websockets
import json
import logging
from typing import Dict, Set
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameServer:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.clients: Set[websockets.WebSocketServerProtocol] = set()

    async def register_client(self, websocket):
        """Register new client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}. Total: {len(self.clients)}")

    async def unregister_client(self, websocket):
        """Handle client disconnection"""
        self.clients.discard(websocket)

        # Remove from any active sessions
        sessions_to_remove = []
        for session_id, session in self.sessions.items():
            if websocket in [session.get('host'), session.get('guest')]:
                sessions_to_remove.append(session_id)
                # Notify other player about disconnection
                other_player = session.get('guest') if session.get('host') == websocket else session.get('host')
                if other_player and other_player in self.clients:
                    try:
                        await other_player.send(json.dumps({
                            "type": "player_disconnected",
                            "session_id": session_id
                        }))
                    except:
                        pass

        for session_id in sessions_to_remove:
            del self.sessions[session_id]

        logger.info(f"Client disconnected: {websocket.remote_address}. Remaining: {len(self.clients)}")

    async def handle_message(self, websocket, message):
        """Handle incoming messages from clients"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "create_session":
                await self.create_session(websocket, data)
            elif msg_type == "join_session":
                await self.join_session(websocket, data)
            elif msg_type == "game_message":
                await self.relay_game_message(websocket, data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def create_session(self, websocket, data):
        """Create new game session"""
        session_id = str(uuid.uuid4())
        player_name = data.get("player_name", "Host")
        player_avatar = data.get("player_avatar", "🙂")

        self.sessions[session_id] = {
            "host": websocket,
            "guest": None,
            "host_info": {
                "name": player_name,
                "avatar": player_avatar
            },
            "guest_info": None,
            "game_state": "waiting"
        }

        invite_code = session_id[:8].upper()

        await websocket.send(json.dumps({
            "type": "session_created",
            "session_id": session_id,
            "invite_code": invite_code
        }))

        logger.info(f"Session {invite_code} created")

    async def join_session(self, websocket, data):
        """Join existing game session"""
        invite_code = data.get("invite_code", "").upper()
        player_name = data.get("player_name", "Guest")
        player_avatar = data.get("player_avatar", "😎")

        # Find session by invite code
        session_id = None
        for sid in self.sessions:
            if sid[:8].upper() == invite_code:
                session_id = sid
                break

        if not session_id or session_id not in self.sessions:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Session not found"
            }))
            return

        session = self.sessions[session_id]

        if session["guest"] is not None:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Session full"
            }))
            return

        # Add guest to session
        session["guest"] = websocket
        session["guest_info"] = {
            "name": player_name,
            "avatar": player_avatar
        }
        session["game_state"] = "ready"

        # Notify host
        await session["host"].send(json.dumps({
            "type": "player_joined",
            "guest_info": session["guest_info"]
        }))

        # Notify guest
        await websocket.send(json.dumps({
            "type": "session_joined",
            "session_id": session_id,
            "host_info": session["host_info"]
        }))

        # Start game
        await asyncio.sleep(0.5)
        start_message = {
            "type": "game_ready",
            "session_id": session_id
        }

        await session["host"].send(json.dumps(start_message))
        await session["guest"].send(json.dumps(start_message))

        logger.info(f"Game ready in session {invite_code}")

    async def relay_game_message(self, websocket, data):
        """Relay game messages between players"""
        session_id = data.get("session_id")
        game_data = data.get("data")

        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]

        # Determine target player
        if websocket == session["host"] and session["guest"]:
            target = session["guest"]
        elif websocket == session["guest"] and session["host"]:
            target = session["host"]
        else:
            return

        # Relay message
        if target in self.clients:
            try:
                await target.send(json.dumps({
                    "type": "game_message",
                    "data": game_data
                }))
            except:
                pass

    async def handle_client(self, websocket, path):
        """Handle individual client connection"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            await self.unregister_client(websocket)


async def start_server(host="0.0.0.0", port=8765):
    """Start the WebSocket server"""
    server = GameServer()
    logger.info(f"Starting WebSocket server on {host}:{port}")

    try:
        async with websockets.serve(server.handle_client, host, port):
            logger.info("WebSocket server running. Press Ctrl+C to stop.")
            await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("WebSocket server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")


if __name__ == "__main__":
    asyncio.run(start_server())