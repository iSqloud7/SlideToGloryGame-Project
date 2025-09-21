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
        """Register a new client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}. Total: {len(self.clients)}")

    async def unregister_client(self, websocket):
        """Unregister a client and clean up their sessions"""
        self.clients.discard(websocket)

        sessions_to_remove = []
        for session_id, session in self.sessions.items():
            if websocket in [session.get('host'), session.get('guest')]:
                sessions_to_remove.append(session_id)
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
            logger.info(f"Cleaned up session {session_id[:8]}")

        logger.info(f"Client disconnected: {websocket.remote_address}. Remaining: {len(self.clients)}")

    async def handle_message(self, websocket, message):
        """Process incoming messages from clients"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            logger.debug(f"Received message type: {msg_type}")

            # Handle ping/pong for connection testing
            if msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
                logger.debug("Sent pong response")
            elif msg_type == "create_session":
                await self.create_session(websocket, data)
            elif msg_type == "join_session":
                await self.join_session(websocket, data)
            elif msg_type == "game_message":
                await self.relay_game_message(websocket, data)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            try:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except:
                pass
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            try:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Internal server error"
                }))
            except:
                pass

    async def create_session(self, websocket, data):
        """Create a new game session"""
        try:
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

            logger.info(f"Session {invite_code} created by {player_name}")

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            try:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Failed to create session"
                }))
            except:
                pass

    async def join_session(self, websocket, data):
        """Join an existing game session"""
        try:
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

            # Check if session is full
            if session["guest"] is not None:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Session is full"
                }))
                return

            # Add guest to session
            session["guest"] = websocket
            session["guest_info"] = {
                "name": player_name,
                "avatar": player_avatar
            }
            session["game_state"] = "ready"

            # Notify host about guest joining
            if session["host"] and session["host"] in self.clients:
                await session["host"].send(json.dumps({
                    "type": "player_joined",
                    "guest_info": session["guest_info"]
                }))

            # Confirm join to guest
            await websocket.send(json.dumps({
                "type": "session_joined",
                "session_id": session_id,
                "host_info": session["host_info"]
            }))

            # Start game after brief delay
            await asyncio.sleep(0.5)
            start_message = {
                "type": "game_ready",
                "session_id": session_id
            }

            # Send game ready to both players
            if session["host"] and session["host"] in self.clients:
                await session["host"].send(json.dumps(start_message))
            if session["guest"] and session["guest"] in self.clients:
                await session["guest"].send(json.dumps(start_message))

            logger.info(
                f"Game ready in session {invite_code} - {session['host_info']['name']} vs {session['guest_info']['name']}")

        except Exception as e:
            logger.error(f"Error joining session: {e}")
            try:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Failed to join session"
                }))
            except:
                pass

    async def relay_game_message(self, websocket, data):
        """Relay game messages between players"""
        try:
            session_id = data.get("session_id")
            game_data = data.get("data")

            if session_id not in self.sessions:
                logger.warning(f"Game message for unknown session: {session_id}")
                return

            session = self.sessions[session_id]

            # Determine target (the other player)
            if websocket == session["host"] and session["guest"]:
                target = session["guest"]
            elif websocket == session["guest"] and session["host"]:
                target = session["host"]
            else:
                logger.warning("Game message from unknown sender")
                return

            # Send message to target if they're still connected
            if target in self.clients:
                try:
                    await target.send(json.dumps({
                        "type": "game_message",
                        "data": game_data
                    }))
                    logger.debug(f"Relayed game message in session {session_id[:8]}")
                except websockets.exceptions.ConnectionClosed:
                    logger.info("Target player disconnected during message relay")
                    await self.unregister_client(target)
                except Exception as e:
                    logger.error(f"Error relaying message: {e}")
            else:
                logger.warning("Target player not in active clients")

        except Exception as e:
            logger.error(f"Error in relay_game_message: {e}")

    async def handle_client(self, websocket, path=None):
        """
        Handle a client connection
        Made path optional for compatibility with different websockets library versions
        """
        await self.register_client(websocket)
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.debug("Client connection closed normally")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            await self.unregister_client(websocket)


async def start_server(host="0.0.0.0", port=8765):
    """Start the WebSocket server"""
    server = GameServer()
    logger.info(f"Starting WebSocket server on {host}:{port}")

    try:
        # Create server with the handler
        server_coroutine = websockets.serve(server.handle_client, host, port)
        server_instance = await server_coroutine

        logger.info("WebSocket server running. Press Ctrl+C to stop.")
        logger.info(f"Server listening on ws://{host}:{port}")

        # Keep server running indefinitely
        await server_instance.wait_closed()

    except KeyboardInterrupt:
        logger.info("WebSocket server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Failed to start server: {e}")