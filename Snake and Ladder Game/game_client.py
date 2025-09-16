#!/usr/bin/env python3
"""
Clean Game Client for Snake & Ladder
Handles authentication, WebSocket communication, and game UI
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os
import requests
import threading
import time
import asyncio
import websockets
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import game logic
from snake_ladder_core import SnakeLadderGame

AUTH_SERVER = "http://localhost:8000"
WEBSOCKET_SERVER = "ws://localhost:8765"


class GameClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Snake & Ladder Game")
        self.root.configure(bg="#2a9d8f")

        # User state
        self.current_user = None
        self.user_data = {}
        self.display_name = "Player"
        self.display_avatar = "🙂"

        # WebSocket connection
        self.websocket = None
        self.session_id = None
        self.invite_code = None
        self.is_host = False
        self.peer_info = None
        self.game_instance = None

        # HTTP session with retry
        self.http_session = self.create_http_session()

        # Load local profile
        self.load_local_profile()

        # Check server and show appropriate window
        self.check_servers()

    def create_http_session(self):
        """Create HTTP session with retry logic"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        return session

    def load_local_profile(self):
        """Load local profile settings"""
        try:
            if os.path.exists("profile.json"):
                with open("profile.json", "r") as f:
                    profile = json.load(f)
                    self.display_name = profile.get("name", "Player")
                    self.display_avatar = profile.get("avatar", "🙂")
        except:
            pass

    def save_local_profile(self):
        """Save local profile settings"""
        try:
            with open("profile.json", "w") as f:
                json.dump({
                    "name": self.display_name,
                    "avatar": self.display_avatar
                }, f)
        except:
            pass

    def check_servers(self):
        """Check if servers are running"""
        auth_ok = self.check_auth_server()
        ws_ok = self.check_websocket_server()

        if auth_ok:
            self.show_login_screen()
        elif ws_ok:
            messagebox.showwarning(
                "Auth Server Offline",
                "Auth server is not available. You can play offline multiplayer only."
            )
            self.current_user = "offline"
            self.show_main_menu(offline=True)
        else:
            messagebox.showerror(
                "Servers Offline",
                "Both auth and WebSocket servers are offline. Only solo play available."
            )
            self.current_user = "offline"
            self.show_main_menu(solo_only=True)

    def check_auth_server(self):
        """Check if auth server is available"""
        try:
            response = self.http_session.get(f"{AUTH_SERVER}/status", timeout=5)
            return response.status_code == 200
        except:
            return False

    def check_websocket_server(self):
        """Check if WebSocket server is available"""
        try:
            import asyncio

            async def test_connection():
                try:
                    async with websockets.connect(WEBSOCKET_SERVER, open_timeout=3) as ws:
                        await ws.send('{"type": "ping"}')
                        return True
                except:
                    return False

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(test_connection())
            loop.close()
            return result
        except:
            return False

    def clear_window(self):
        """Clear all widgets from window"""
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login_screen(self):
        """Show login/register screen"""
        self.clear_window()
        self.root.geometry("450x500")
        self.root.title("Snake & Ladder - Login")

        # Header
        header = tk.Frame(self.root, bg="#34495e", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🐍 Snake & Ladder", font=("Arial", 20, "bold"),
                 bg="#34495e", fg="white").pack(pady=20)

        # Main form
        form = tk.Frame(self.root, bg="#2a9d8f", padx=40, pady=30)
        form.pack(expand=True, fill="both")

        tk.Label(form, text="Login / Register", font=("Arial", 16, "bold"),
                 bg="#2a9d8f", fg="white").pack(pady=15)

        # Username
        tk.Label(form, text="Username:", font=("Arial", 12, "bold"),
                 bg="#2a9d8f", fg="white").pack(anchor="w", pady=(10, 5))

        self.username_entry = tk.Entry(form, font=("Arial", 12), width=25)
        self.username_entry.pack(pady=5, ipady=8)

        # Password
        tk.Label(form, text="Password:", font=("Arial", 12, "bold"),
                 bg="#2a9d8f", fg="white").pack(anchor="w", pady=(15, 5))

        self.password_entry = tk.Entry(form, font=("Arial", 12), width=25, show="*")
        self.password_entry.pack(pady=5, ipady=8)

        # Buttons
        button_frame = tk.Frame(form, bg="#2a9d8f")
        button_frame.pack(pady=25)

        tk.Button(button_frame, text="Login", command=self.handle_login,
                  font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                  padx=20, pady=10, width=12).pack(pady=5)

        tk.Button(button_frame, text="Register", command=self.handle_register,
                  font=("Arial", 14, "bold"), bg="#2980b9", fg="white",
                  padx=20, pady=10, width=12).pack(pady=5)

        tk.Button(button_frame, text="Play Offline", command=self.play_offline,
                  font=("Arial", 12), bg="#95a5a6", fg="white",
                  padx=15, pady=8, width=12).pack(pady=10)

        # Status
        self.status_label = tk.Label(form, text="", font=("Arial", 10),
                                     bg="#2a9d8f", fg="white", wraplength=350)
        self.status_label.pack(pady=10)

        # Key bindings
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self.handle_login())
        self.username_entry.focus()

    def handle_login(self):
        """Handle user login"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            self.status_label.config(text="Please enter username and password", fg="#e74c3c")
            return

        self.status_label.config(text="Logging in...", fg="#f1c40f")
        self.root.update()

        try:
            response = self.http_session.post(
                f"{AUTH_SERVER}/login",
                json={"username": username, "password": password},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                self.current_user = result.get("username", username)
                self.user_data = result.get("user_data", {})
                self.display_name = self.current_user

                self.status_label.config(text="Login successful!", fg="#27ae60")
                self.root.after(1000, self.show_main_menu)
            else:
                error = response.json().get("detail", "Login failed")
                self.status_label.config(text=f"Error: {error}", fg="#e74c3c")

        except requests.exceptions.Timeout:
            self.status_label.config(text="Server timeout", fg="#e74c3c")
        except Exception as e:
            self.status_label.config(text="Connection error", fg="#e74c3c")

    def handle_register(self):
        """Handle user registration"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            self.status_label.config(text="Please enter username and password", fg="#e74c3c")
            return

        if len(username) < 3:
            self.status_label.config(text="Username must be at least 3 characters", fg="#e74c3c")
            return

        if len(password) < 4:
            self.status_label.config(text="Password must be at least 4 characters", fg="#e74c3c")
            return

        self.status_label.config(text="Registering...", fg="#f1c40f")
        self.root.update()

        try:
            response = self.http_session.post(
                f"{AUTH_SERVER}/register",
                json={"username": username, "password": password},
                timeout=10
            )

            if response.status_code == 200:
                self.status_label.config(text="Registration successful! Please login.", fg="#27ae60")
                self.password_entry.delete(0, tk.END)
            else:
                error = response.json().get("detail", "Registration failed")
                self.status_label.config(text=f"Error: {error}", fg="#e74c3c")

        except requests.exceptions.Timeout:
            self.status_label.config(text="Server timeout", fg="#e74c3c")
        except Exception as e:
            self.status_label.config(text="Connection error", fg="#e74c3c")

    def play_offline(self):
        """Switch to offline mode"""
        self.current_user = "offline"
        self.display_name = self.display_name or "Player"
        messagebox.showinfo("Offline Mode", "Playing in offline mode. Online features disabled.")
        self.show_main_menu(offline=True)

    def show_main_menu(self, offline=False, solo_only=False):
        """Show main game menu"""
        self.clear_window()
        self.root.geometry("600x650")
        self.root.title(f"Snake & Ladder - {self.display_name}")

        # Header
        header = tk.Frame(self.root, bg="#34495e", height=100)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🐍 Snake & Ladder", font=("Arial", 24, "bold"),
                 bg="#34495e", fg="white").pack(pady=15)

        status_text = "Offline Mode" if offline else "Online Mode"
        if solo_only:
            status_text = "Solo Mode Only"

        tk.Label(header, text=status_text, font=("Arial", 12),
                 bg="#34495e", fg="#bdc3c7").pack()

        tk.Label(header, text=f"Playing as: {self.display_avatar} {self.display_name}",
                 font=("Arial", 14, "bold"), bg="#34495e", fg="#f1c40f").pack(pady=5)

        # Main content
        content = tk.Frame(self.root, bg="#2c3e50", padx=40, pady=30)
        content.pack(expand=True, fill="both")

        tk.Label(content, text="Choose Game Mode", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=20)

        # Game buttons
        tk.Button(content, text="🎮 Play Solo (vs Bot)", font=("Arial", 16, "bold"),
                  command=self.start_solo_game, bg="#e74c3c", fg="white",
                  padx=25, pady=12, width=25).pack(pady=10)

        if not solo_only:
            tk.Button(content, text="🌐 Host Multiplayer Game", font=("Arial", 16, "bold"),
                      command=self.host_multiplayer, bg="#27ae60", fg="white",
                      padx=25, pady=12, width=25).pack(pady=10)

            tk.Button(content, text="🔗 Join Multiplayer Game", font=("Arial", 16, "bold"),
                      command=self.join_multiplayer, bg="#3498db", fg="white",
                      padx=25, pady=12, width=25).pack(pady=10)

        # Profile and logout
        button_frame = tk.Frame(content, bg="#2c3e50")
        button_frame.pack(pady=20)

        tk.Button(button_frame, text="👤 Edit Profile", command=self.show_profile,
                  font=("Arial", 14), bg="#9b59b6", fg="white",
                  padx=15, pady=8, width=12).pack(side=tk.LEFT, padx=5)

        if not offline:
            tk.Button(button_frame, text="🚪 Logout", command=self.logout,
                      font=("Arial", 14), bg="#e67e22", fg="white",
                      padx=15, pady=8, width=10).pack(side=tk.RIGHT, padx=5)

        # Show user stats if available
        if self.user_data:
            self.show_user_stats(content)

    def show_user_stats(self, parent):
        """Display user statistics"""
        stats_frame = tk.Frame(parent, bg="#34495e", relief=tk.RAISED, bd=2)
        stats_frame.pack(pady=15, padx=20, fill="x")

        tk.Label(stats_frame, text="📊 Your Statistics", font=("Arial", 14, "bold"),
                 bg="#34495e", fg="white").pack(pady=8)

        games = self.user_data.get('games_played', 0)
        wins = self.user_data.get('wins', 0)
        losses = self.user_data.get('losses', 0)

        tk.Label(stats_frame, text=f"Games: {games} • Wins: {wins} • Losses: {losses}",
                 font=("Arial", 11), bg="#34495e", fg="#27ae60").pack(pady=5)

    def show_profile(self):
        """Show profile editing window"""
        profile_window = tk.Toplevel(self.root)
        profile_window.title("Edit Profile")
        profile_window.geometry("400x350")
        profile_window.configure(bg="#2c3e50")

        tk.Label(profile_window, text="👤 Edit Profile", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=15)

        # Avatar selection
        tk.Label(profile_window, text="Choose Avatar:", font=("Arial", 14),
                 bg="#2c3e50", fg="#bdc3c7").pack(pady=(15, 10))

        avatars = ["🙂", "😎", "🤖", "🐍", "🐱", "🐯", "🐸", "🐧", "🚀", "⚡"]
        selected_avatar = tk.StringVar(value=self.display_avatar)

        avatar_frame = tk.Frame(profile_window, bg="#2c3e50")
        avatar_frame.pack(pady=10)

        for i, emoji in enumerate(avatars):
            row = i // 5
            col = i % 5
            tk.Radiobutton(avatar_frame, text=emoji, variable=selected_avatar,
                           value=emoji, font=("Arial", 16), bg="#34495e",
                           fg="white", selectcolor="#3498db",
                           indicatoron=False, width=3).grid(row=row, column=col, padx=2, pady=2)

        # Name entry
        tk.Label(profile_window, text="Display Name:", font=("Arial", 14),
                 bg="#2c3e50", fg="#bdc3c7").pack(pady=(20, 5))

        name_entry = tk.Entry(profile_window, font=("Arial", 12), width=20)
        name_entry.insert(0, self.display_name)
        name_entry.pack(pady=5, ipady=5)

        def save_profile():
            new_name = name_entry.get().strip() or "Player"
            new_avatar = selected_avatar.get()

            self.display_name = new_name
            self.display_avatar = new_avatar
            self.save_local_profile()

            messagebox.showinfo("Profile Updated", f"Profile updated!\nName: {new_name}\nAvatar: {new_avatar}")
            profile_window.destroy()
            self.show_main_menu()

        tk.Button(profile_window, text="💾 Save Profile", command=save_profile,
                  font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                  padx=20, pady=10).pack(pady=20)

    def logout(self):
        """Logout user"""
        self.current_user = None
        self.user_data = {}
        self.show_login_screen()

    def start_solo_game(self):
        """Start solo game against bot"""
        self.start_game(
            mode="solo",
            player_names=[self.display_name, "Bot"],
            player_avatars=[self.display_avatar, "🤖"]
        )

    def host_multiplayer(self):
        """Host multiplayer game"""
        if not self.websocket:
            threading.Thread(target=self._host_game_thread, daemon=True).start()
            self.show_waiting_dialog("Creating game session...")

    def join_multiplayer(self):
        """Join multiplayer game"""
        invite_code = simpledialog.askstring("Join Game", "Enter invite code:")
        if invite_code and len(invite_code.strip()) == 8:
            threading.Thread(target=self._join_game_thread, args=(invite_code.strip(),), daemon=True).start()
            self.show_waiting_dialog(f"Joining game {invite_code.upper()}...")
        else:
            messagebox.showerror("Invalid Code", "Please enter a valid 8-character invite code")

    def show_waiting_dialog(self, message):
        """Show waiting dialog during connection"""
        self.waiting_window = tk.Toplevel(self.root)
        self.waiting_window.title("Connecting")
        self.waiting_window.geometry("350x150")
        self.waiting_window.configure(bg="#2c3e50")
        self.waiting_window.transient(self.root)

        tk.Label(self.waiting_window, text="🌐 Connecting", font=("Arial", 16, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=20)

        self.waiting_label = tk.Label(self.waiting_window, text=message, font=("Arial", 12),
                                      bg="#2c3e50", fg="#bdc3c7", wraplength=300)
        self.waiting_label.pack(pady=10)

        tk.Button(self.waiting_window, text="Cancel", command=self._cancel_connection,
                  font=("Arial", 12), bg="#e74c3c", fg="white",
                  padx=15, pady=5).pack(pady=15)

    def _cancel_connection(self):
        """Cancel connection attempt"""
        if self.websocket:
            try:
                asyncio.create_task(self.websocket.close())
            except:
                pass
            self.websocket = None

        if hasattr(self, 'waiting_window'):
            self.waiting_window.destroy()

    def _host_game_thread(self):
        """Thread for hosting game"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._host_game_async())
        except Exception as e:
            print(f"Host game error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Connection Failed", "Failed to host game"))

    def _join_game_thread(self, invite_code):
        """Thread for joining game"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._join_game_async(invite_code))
        except Exception as e:
            print(f"Join game error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Connection Failed", "Failed to join game"))

    async def _host_game_async(self):
        """Async host game logic"""
        try:
            self.websocket = await websockets.connect(WEBSOCKET_SERVER)
            self.is_host = True

            # Send create session request
            await self.websocket.send(json.dumps({
                "type": "create_session",
                "player_name": self.display_name,
                "player_avatar": self.display_avatar
            }))

            # Listen for messages
            await self._handle_websocket_messages()

        except Exception as e:
            print(f"Host async error: {e}")

    async def _join_game_async(self, invite_code):
        """Async join game logic"""
        try:
            self.websocket = await websockets.connect(WEBSOCKET_SERVER)
            self.is_host = False

            # Send join session request
            await self.websocket.send(json.dumps({
                "type": "join_session",
                "invite_code": invite_code.upper(),
                "player_name": self.display_name,
                "player_avatar": self.display_avatar
            }))

            # Listen for messages
            await self._handle_websocket_messages()

        except Exception as e:
            print(f"Join async error: {e}")

    async def _handle_websocket_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._process_websocket_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
        except Exception as e:
            print(f"WebSocket message handling error: {e}")

    async def _process_websocket_message(self, data):
        """Process WebSocket message"""
        msg_type = data.get("type")

        if msg_type == "session_created":
            self.session_id = data.get("session_id")
            self.invite_code = data.get("invite_code")
            self.root.after(0, lambda: self.waiting_label.config(
                text=f"Session created!\nInvite code: {self.invite_code}\nWaiting for player..."
            ))

        elif msg_type == "player_joined":
            self.peer_info = data.get("guest_info")

        elif msg_type == "session_joined":
            self.session_id = data.get("session_id")
            self.peer_info = data.get("host_info")

        elif msg_type == "game_ready":
            self.root.after(0, self._start_multiplayer_game)

        elif msg_type == "game_message":
            if self.game_instance:
                self.game_instance.handle_network_message(data.get("data"))

        elif msg_type == "player_disconnected":
            self.root.after(0, lambda: messagebox.showinfo("Player Disconnected", "Other player left the game"))
            if self.game_instance:
                self.game_instance.handle_disconnect()

        elif msg_type == "error":
            error_msg = data.get("message", "Unknown error")
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self._cancel_connection()

    def _start_multiplayer_game(self):
        """Start multiplayer game"""
        if hasattr(self, 'waiting_window'):
            self.waiting_window.destroy()

        if not self.peer_info:
            messagebox.showerror("Error", "Peer information not available")
            return

        # Set up player info
        if self.is_host:
            player_names = [self.display_name, self.peer_info.get('name', 'Guest')]
            player_avatars = [self.display_avatar, self.peer_info.get('avatar', '😎')]
        else:
            player_names = [self.peer_info.get('name', 'Host'), self.display_name]
            player_avatars = [self.peer_info.get('avatar', '🙂'), self.display_avatar]

        self.start_game(
            mode="multiplayer",
            player_names=player_names,
            player_avatars=player_avatars
        )

    def start_game(self, mode, player_names, player_avatars):
        """Start game with specified parameters"""
        # Minimize main window
        self.root.iconify()

        # Create game window
        game_window = tk.Toplevel(self.root)
        game_window.title("Snake & Ladder Game")
        game_window.lift()
        game_window.focus_force()

        # Create game instance
        try:
            self.game_instance = SnakeLadderGame(
                window=game_window,
                player_names=player_names,
                player_avatars=player_avatars,
                mode=mode,
                websocket_connection=WebSocketConnection(self.websocket,
                                                         self.session_id) if mode == "multiplayer" else None,
                is_host=self.is_host if mode == "multiplayer" else True,
                on_game_end=self.on_game_end
            )
        except Exception as e:
            messagebox.showerror("Game Error", f"Failed to start game: {e}")
            self.root.deiconify()

    def on_game_end(self, winner_idx):
        """Handle game end"""
        # Show main window
        self.root.deiconify()

        # Close WebSocket connection
        if self.websocket:
            try:
                asyncio.create_task(self.websocket.close())
            except:
                pass
            self.websocket = None

        # Reset state
        self.session_id = None
        self.invite_code = None
        self.peer_info = None
        self.game_instance = None

        # Show main menu
        self.show_main_menu()

    def run(self):
        """Run the application"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            print(f"Application error: {e}")
        finally:
            if self.websocket:
                try:
                    asyncio.create_task(self.websocket.close())
                except:
                    pass

    def on_closing(self):
        """Handle application closing"""
        if self.websocket:
            try:
                asyncio.create_task(self.websocket.close())
            except:
                pass
        self.root.destroy()


class WebSocketConnection:
    """Helper class for WebSocket communication in game"""

    def __init__(self, websocket, session_id):
        self.websocket = websocket
        self.session_id = session_id

    def send_message(self, data):
        """Send game message through WebSocket"""
        if self.websocket:
            try:
                message = {
                    "type": "game_message",
                    "session_id": self.session_id,
                    "data": data
                }
                asyncio.create_task(self.websocket.send(json.dumps(message)))
                return True
            except:
                return False
        return False


if __name__ == "__main__":
    client = GameClient()
    client.run()