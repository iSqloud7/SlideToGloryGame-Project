import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os
import requests
import threading
import time
import asyncio
import websockets
import inspect
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from snake_ladder_core import SnakeLadderGame

AUTH_SERVER = "https://0a6e78084c88.ngrok-free.app"
WEBSOCKET_SERVER = "wss://cf049d2e9172.ngrok-free.app"


def load_server_config():
    config_file = "server_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('auth_server'), config.get('websocket_server')
        except:
            pass
    return None, None


config_auth, config_ws = load_server_config()
if config_auth and config_ws:
    AUTH_SERVER = config_auth
    WEBSOCKET_SERVER = config_ws


class GameClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Slide to Glory Game")
        self.root.configure(bg="#2a9d8f")

        self.current_user = None
        # Start with empty user_data - don't initialize defaults yet
        self.user_data = {}
        self.display_name = "Player"
        self.display_avatar = "🙂"

        self.websocket = None
        self.session_id = None
        self.invite_code = None
        self.is_host = False
        self.peer_info = None
        self.game_instance = None

        self.http_session = self.create_http_session()

        # Load local profile and stats FIRST
        self.load_local_profile()
        self.load_local_stats()  # Add this line

        # Only initialize defaults AFTER trying to load existing stats
        self.initialize_user_data()

        self.check_servers()
    def initialize_user_data(self):
        """Initialize user_data with default values if not already loaded"""
        default_data = {
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "fastest_win": None
        }

        # Only set defaults for missing keys, don't overwrite existing data
        for key, default_value in default_data.items():
            if key not in self.user_data:
                self.user_data[key] = default_value

        print(f"User data initialized: {self.user_data}")

    def create_http_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def load_local_profile(self):
        try:
            if os.path.exists("profile.json"):
                with open("profile.json", "r") as f:
                    profile = json.load(f)
                    self.display_name = profile.get("name", "Player")
                    self.display_avatar = profile.get("avatar", "🙂")
        except:
            pass

    def load_local_stats(self):
        """Load stats from local file, preserving existing values if file doesn't exist"""
        try:
            if os.path.exists("stats.json"):
                with open("stats.json", "r") as f:
                    loaded_data = json.load(f)
                    # Update user_data with loaded values, but don't overwrite if user_data already has values
                    for key, value in loaded_data.items():
                        self.user_data[key] = value
                    print(f"Loaded local stats: {loaded_data}")
            else:
                print("No stats.json file found - keeping current stats")
        except Exception as e:
            print(f"Error loading local stats: {e}")
            # Don't reset user_data on error

    def save_local_stats(self):
        with open("stats.json", "w") as f:
            json.dump(self.user_data, f)

    def save_local_profile(self):
        try:
            with open("profile.json", "w") as f:
                json.dump({
                    "name": self.display_name,
                    "avatar": self.display_avatar
                }, f)
        except:
            pass

    def check_servers(self):
        print(f"Checking servers...")
        print(f"Auth server: {AUTH_SERVER}")
        print(f"WebSocket server: {WEBSOCKET_SERVER}")

        auth_ok = self.check_auth_server()
        ws_ok = self.check_websocket_server()

        print(f"Auth server status: {'OK' if auth_ok else 'OFFLINE'}")
        print(f"WebSocket server status: {'OK' if ws_ok else 'OFFLINE'}")

        if auth_ok:
            self.show_welcome_screen()
        elif ws_ok:
            messagebox.showwarning(
                "Auth Server Offline",
                "Auth server is not available. You can play offline multiplayer only."
            )
            self.current_user = "offline"
            # Load stats for offline mode, but don't overwrite existing stats
            self.load_local_stats()
            self.initialize_user_data()  # Only fill in missing fields
            self.show_main_menu(offline=True)
        else:
            messagebox.showerror(
                "Servers Offline",
                f"Both servers are offline.\n\nChecked URLs:\nAuth: {AUTH_SERVER}\nWebSocket: {WEBSOCKET_SERVER}\n\nOnly solo play available."
            )
            self.current_user = "offline"
            # Load stats for offline mode, but don't overwrite existing stats
            self.load_local_stats()
            self.initialize_user_data()  # Only fill in missing fields
            self.show_main_menu(solo_only=True)

    def check_auth_server(self):
        try:
            print(f"Testing auth server at: {AUTH_SERVER}")
            headers = {
                'ngrok-skip-browser-warning': 'true',
                'User-Agent': 'SnakeLadderGame/1.0'
            }
            response = self.http_session.get(f"{AUTH_SERVER}/status", timeout=10, headers=headers)
            print(f"Auth server response: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"Auth server check failed: {e}")
            return False

    def check_websocket_server(self):
        try:
            print(f"Testing WebSocket server at: {WEBSOCKET_SERVER}")

            async def test_connection():
                try:
                    websocket_kwargs = {'open_timeout': 5}

                    connect_sig = inspect.signature(websockets.connect)
                    if 'extra_headers' in connect_sig.parameters:
                        websocket_kwargs['extra_headers'] = {
                            'User-Agent': 'SnakeLadderGame/1.0'
                        }

                    async with websockets.connect(WEBSOCKET_SERVER, **websocket_kwargs) as ws:
                        await ws.send('{"type": "ping"}')
                        return True
                except Exception as e:
                    print(f"WebSocket test error: {e}")
                    return False

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(test_connection())
            loop.close()
            print(f"WebSocket test result: {'OK' if result else 'FAILED'}")
            return result
        except Exception as e:
            print(f"WebSocket server check failed: {e}")
            return False

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_welcome_screen(self):
        self.clear_window()
        self.root.geometry("500x600")
        self.root.title("Slide to Glory - Welcome")

        # Header
        header = tk.Frame(self.root, bg="#34495e", height=100)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🐍 Slide to Glory", font=("Arial", 24, "bold"),
                 bg="#34495e", fg="white").pack(pady=20)

        # Content
        content = tk.Frame(self.root, bg="#2a9d8f", padx=50, pady=40)
        content.pack(expand=True, fill="both")

        tk.Label(content, text="Welcome to Slide to Glory!", font=("Arial", 18, "bold"),
                 bg="#2a9d8f", fg="white").pack(pady=20)

        tk.Label(content, text="Choose an option to get started:", font=("Arial", 14),
                 bg="#2a9d8f", fg="white").pack(pady=10)

        # Buttons
        button_frame = tk.Frame(content, bg="#2a9d8f")
        button_frame.pack(pady=30)

        tk.Button(button_frame, text="🔑 Login", command=self.show_login_window,
                  font=("Arial", 16, "bold"), bg="#27ae60", fg="white",
                  padx=30, pady=15, width=15).pack(pady=8)

        tk.Button(button_frame, text="📝 Register", command=self.show_register_window,
                  font=("Arial", 16, "bold"), bg="#2980b9", fg="white",
                  padx=30, pady=15, width=15).pack(pady=8)

        tk.Button(button_frame, text="🎮 Play Offline", command=self.play_offline,
                  font=("Arial", 14), bg="#95a5a6", fg="white",
                  padx=25, pady=12, width=15).pack(pady=15)

    def show_login_window(self):
        login_window = tk.Toplevel(self.root)
        login_window.title("Slide to Glory - Login")
        login_window.geometry("450x500")
        login_window.configure(bg="#2a9d8f")
        login_window.transient(self.root)
        login_window.grab_set()

        # Center the window
        login_window.update_idletasks()
        x = (login_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (login_window.winfo_screenheight() // 2) - (500 // 2)
        login_window.geometry(f"450x500+{x}+{y}")

        # Header
        header = tk.Frame(login_window, bg="#34495e", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🔑 Login", font=("Arial", 20, "bold"),
                 bg="#34495e", fg="white").pack(pady=20)

        # Form
        form = tk.Frame(login_window, bg="#2a9d8f", padx=40, pady=30)
        form.pack(expand=True, fill="both")

        tk.Label(form, text="Enter your credentials", font=("Arial", 14),
                 bg="#2a9d8f", fg="white").pack(pady=15)

        tk.Label(form, text="Username:", font=("Arial", 12, "bold"),
                 bg="#2a9d8f", fg="white").pack(anchor="w", pady=(10, 5))

        username_entry = tk.Entry(form, font=("Arial", 12), width=25)
        username_entry.pack(pady=5, ipady=8)

        tk.Label(form, text="Password:", font=("Arial", 12, "bold"),
                 bg="#2a9d8f", fg="white").pack(anchor="w", pady=(15, 5))

        password_entry = tk.Entry(form, font=("Arial", 12), width=25, show="*")
        password_entry.pack(pady=5, ipady=8)

        # Buttons
        button_frame = tk.Frame(form, bg="#2a9d8f")
        button_frame.pack(pady=25)

        def handle_login():
            username = username_entry.get().strip()
            password = password_entry.get().strip()

            if not username or not password:
                status_label.config(text="Please enter username and password", fg="#e74c3c")
                return

            status_label.config(text="Logging in...", fg="#f1c40f")
            login_window.update()

            try:
                headers = {
                    'ngrok-skip-browser-warning': 'true',
                    'User-Agent': 'SnakeLadderGame/1.0',
                    'Content-Type': 'application/json'
                }

                response = self.http_session.post(
                    f"{AUTH_SERVER}/login",
                    json={"username": username, "password": password},
                    timeout=15,
                    headers=headers
                )

                if response.status_code == 200:
                    result = response.json()
                    self.current_user = result.get("username", username)

                    # Smart merging of server and local stats
                    server_user_data = result.get("user_data", {})
                    print(f"Server returned user_data: {server_user_data}")
                    print(f"Local stats before merge: {self.user_data}")

                    if server_user_data:
                        # Merge stats intelligently - take the higher values for cumulative stats
                        merged_stats = {}

                        # For cumulative stats, take the maximum
                        merged_stats["games_played"] = max(
                            server_user_data.get("games_played", 0),
                            self.user_data.get("games_played", 0)
                        )
                        merged_stats["wins"] = max(
                            server_user_data.get("wins", 0),
                            self.user_data.get("wins", 0)
                        )
                        merged_stats["losses"] = max(
                            server_user_data.get("losses", 0),
                            self.user_data.get("losses", 0)
                        )

                        # For fastest_win, take the better (lower) time if both exist
                        server_fastest = server_user_data.get("fastest_win")
                        local_fastest = self.user_data.get("fastest_win")

                        if server_fastest is not None and local_fastest is not None:
                            merged_stats["fastest_win"] = min(server_fastest, local_fastest)
                        elif server_fastest is not None:
                            merged_stats["fastest_win"] = server_fastest
                        elif local_fastest is not None:
                            merged_stats["fastest_win"] = local_fastest
                        else:
                            merged_stats["fastest_win"] = None

                        self.user_data = merged_stats
                        print(f"Stats after smart merge: {self.user_data}")

                        # Save merged stats locally
                        self.save_local_stats()

                        # If local stats were higher, sync them back to server
                        if (merged_stats["games_played"] > server_user_data.get("games_played", 0) or
                                merged_stats["wins"] > server_user_data.get("wins", 0) or
                                merged_stats["losses"] > server_user_data.get("losses", 0)):

                            print("Local stats were higher, syncing to server...")
                            try:
                                sync_response = self.http_session.post(
                                    f"{AUTH_SERVER}/update_stats",
                                    json={"username": self.current_user, "user_data": merged_stats},
                                    headers=headers,
                                    timeout=10
                                )
                                if sync_response.status_code == 200:
                                    print("Successfully synced local stats to server")
                                else:
                                    print(f"Failed to sync stats to server: {sync_response.status_code}")
                            except Exception as e:
                                print(f"Error syncing stats to server: {e}")
                    else:
                        # Server has no user_data, keep local stats and upload them
                        print("Server has no user data, keeping local stats")
                        if any(self.user_data.get(key, 0) > 0 for key in ["games_played", "wins", "losses"]):
                            print("Uploading local stats to server...")
                            try:
                                sync_response = self.http_session.post(
                                    f"{AUTH_SERVER}/update_stats",
                                    json={"username": self.current_user, "user_data": self.user_data},
                                    headers=headers,
                                    timeout=10
                                )
                                if sync_response.status_code == 200:
                                    print("Successfully uploaded local stats to server")
                            except Exception as e:
                                print(f"Error uploading stats to server: {e}")

                    self.display_name = self.current_user

                    status_label.config(text="Login successful!", fg="#27ae60")
                    login_window.after(1000, lambda: [login_window.destroy(), self.show_main_menu()])
                else:
                    error = response.json().get("detail", "Login failed")
                    status_label.config(text=f"Error: {error}", fg="#e74c3c")

            except requests.exceptions.Timeout:
                status_label.config(text="Server timeout", fg="#e74c3c")
            except Exception as e:
                print(f"Login error: {e}")
                status_label.config(text="Connection error", fg="#e74c3c")
        tk.Button(button_frame, text="🔑 Login", command=handle_login,
                  font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                  padx=20, pady=10, width=12).pack(pady=5)

        tk.Button(button_frame, text="❌ Cancel", command=login_window.destroy,
                  font=("Arial", 12), bg="#e74c3c", fg="white",
                  padx=15, pady=8, width=12).pack(pady=5)

        # Status label
        status_label = tk.Label(form, text="", font=("Arial", 10),
                               bg="#2a9d8f", fg="white", wraplength=350)
        status_label.pack(pady=10)

        # Key bindings
        username_entry.bind("<Return>", lambda e: password_entry.focus())
        password_entry.bind("<Return>", lambda e: handle_login())
        username_entry.focus()

    def show_register_window(self):
        register_window = tk.Toplevel(self.root)
        register_window.title("Slide to Glory - Register")
        register_window.geometry("450x550")
        register_window.configure(bg="#2a9d8f")
        register_window.transient(self.root)
        register_window.grab_set()

        # Center the window
        register_window.update_idletasks()
        x = (register_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (register_window.winfo_screenheight() // 2) - (550 // 2)
        register_window.geometry(f"450x550+{x}+{y}")

        # Header
        header = tk.Frame(register_window, bg="#34495e", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="📝 Create Account", font=("Arial", 20, "bold"),
                 bg="#34495e", fg="white").pack(pady=20)

        # Form
        form = tk.Frame(register_window, bg="#2a9d8f", padx=40, pady=30)
        form.pack(expand=True, fill="both")

        tk.Label(form, text="Create your new account", font=("Arial", 14),
                 bg="#2a9d8f", fg="white").pack(pady=15)

        tk.Label(form, text="Username:", font=("Arial", 12, "bold"),
                 bg="#2a9d8f", fg="white").pack(anchor="w", pady=(10, 5))

        username_entry = tk.Entry(form, font=("Arial", 12), width=25)
        username_entry.pack(pady=5, ipady=8)

        tk.Label(form, text="(Minimum 3 characters)", font=("Arial", 9),
                 bg="#2a9d8f", fg="#bdc3c7").pack(anchor="w")

        tk.Label(form, text="Password:", font=("Arial", 12, "bold"),
                 bg="#2a9d8f", fg="white").pack(anchor="w", pady=(15, 5))

        password_entry = tk.Entry(form, font=("Arial", 12), width=25, show="*")
        password_entry.pack(pady=5, ipady=8)

        tk.Label(form, text="(Minimum 4 characters)", font=("Arial", 9),
                 bg="#2a9d8f", fg="#bdc3c7").pack(anchor="w")

        # Buttons
        button_frame = tk.Frame(form, bg="#2a9d8f")
        button_frame.pack(pady=25)

        def handle_register():
            username = username_entry.get().strip()
            password = password_entry.get().strip()

            if not username or not password:
                status_label.config(text="Please enter username and password", fg="#e74c3c")
                return

            if len(username) < 3:
                status_label.config(text="Username must be at least 3 characters", fg="#e74c3c")
                return

            if len(password) < 4:
                status_label.config(text="Password must be at least 4 characters", fg="#e74c3c")
                return

            status_label.config(text="Creating account...", fg="#f1c40f")
            register_window.update()

            try:
                headers = {
                    'ngrok-skip-browser-warning': 'true',
                    'User-Agent': 'SnakeLadderGame/1.0',
                    'Content-Type': 'application/json'
                }

                response = self.http_session.post(
                    f"{AUTH_SERVER}/register",
                    json={"username": username, "password": password},
                    timeout=15,
                    headers=headers
                )

                if response.status_code == 200:
                    status_label.config(text="Account created successfully!", fg="#27ae60")
                    messagebox.showinfo("Registration Successful",
                                      "Account created successfully!\nYou can now login with your credentials.")
                    register_window.destroy()
                else:
                    error = response.json().get("detail", "Registration failed")
                    status_label.config(text=f"Error: {error}", fg="#e74c3c")

            except requests.exceptions.Timeout:
                status_label.config(text="Server timeout", fg="#e74c3c")
            except Exception as e:
                print(f"Register error: {e}")
                status_label.config(text="Connection error", fg="#e74c3c")

        tk.Button(button_frame, text="📝 Create Account", command=handle_register,
                  font=("Arial", 14, "bold"), bg="#2980b9", fg="white",
                  padx=20, pady=10, width=14).pack(pady=5)

        tk.Button(button_frame, text="❌ Cancel", command=register_window.destroy,
                  font=("Arial", 12), bg="#e74c3c", fg="white",
                  padx=15, pady=8, width=14).pack(pady=5)

        # Status label
        status_label = tk.Label(form, text="", font=("Arial", 10),
                               bg="#2a9d8f", fg="white", wraplength=350)
        status_label.pack(pady=10)

        # Key bindings
        username_entry.bind("<Return>", lambda e: password_entry.focus())
        password_entry.bind("<Return>", lambda e: handle_register())
        username_entry.focus()

    def play_offline(self):
        self.current_user = "offline"
        self.display_name = self.display_name or "Player"

        # Load local stats for offline play - this should preserve existing stats
        self.load_local_stats()

        # Initialize any missing stats with defaults (don't overwrite existing values)
        self.initialize_user_data()

        print(f"Playing offline with stats: {self.user_data}")
        messagebox.showinfo("Offline Mode", "Playing in offline mode. Online features disabled.")
        self.show_main_menu(offline=True)

    def show_main_menu(self, offline=False, solo_only=False):
        # Ensure stats are loaded when showing main menu in offline mode
        if offline or solo_only:
            self.load_local_stats()
            self.initialize_user_data()

        self.clear_window()
        self.root.geometry("600x650")
        self.root.title(f"Snake & Ladder - {self.display_name}")

        header = tk.Frame(self.root, bg="#34495e", height=100)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🐍 Slide to Glory", font=("Arial", 24, "bold"),
                 bg="#34495e", fg="white").pack(pady=15)

        status_text = "Offline Mode" if offline else "Online Mode"
        if solo_only:
            status_text = "Solo Mode Only"

        tk.Label(header, text=status_text, font=("Arial", 12),
                 bg="#34495e", fg="#bdc3c7").pack()

        tk.Label(header, text=f"Playing as: {self.display_avatar} {self.display_name}",
                 font=("Arial", 14, "bold"), bg="#34495e", fg="#f1c40f").pack(pady=5)

        content = tk.Frame(self.root, bg="#2c3e50", padx=40, pady=30)
        content.pack(expand=True, fill="both")

        tk.Label(content, text="Choose Game Mode", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=20)

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

        button_frame = tk.Frame(content, bg="#2c3e50")
        button_frame.pack(pady=20)

        tk.Button(button_frame, text="👤 Edit Profile", command=self.show_profile,
                  font=("Arial", 14), bg="#9b59b6", fg="white",
                  padx=15, pady=8, width=12).pack(side=tk.LEFT, padx=5)

        if not offline:
            tk.Button(button_frame, text="🚪 Logout", command=self.logout,
                      font=("Arial", 14), bg="#e67e22", fg="white",
                      padx=15, pady=8, width=10).pack(side=tk.RIGHT, padx=5)

        if self.user_data:
            self.show_user_stats(content)

    def show_user_stats(self, parent):
        stats_frame = tk.Frame(parent, bg="#34495e", relief=tk.RAISED, bd=2)
        stats_frame.pack(pady=15, padx=20, fill="x")

        tk.Label(stats_frame, text="📊 Your Statistics", font=("Arial", 14, "bold"),
                 bg="#34495e", fg="white").pack(pady=8)

        games = self.user_data.get('games_played', 0)
        wins = self.user_data.get('wins', 0)
        losses = self.user_data.get('losses', 0)
        fastest_win = self.user_data.get('fastest_win')

        tk.Label(stats_frame, text=f"Games: {games} • Wins: {wins} • Losses: {losses}",
                 font=("Arial", 11), bg="#34495e", fg="#27ae60").pack(pady=5)

        if fastest_win:
            minutes = fastest_win // 60
            seconds = fastest_win % 60
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            tk.Label(stats_frame, text=f"⚡ Fastest Win: {time_str}",
                     font=("Arial", 11), bg="#34495e", fg="#f1c40f").pack(pady=5)

    def show_profile(self):
        profile_window = tk.Toplevel(self.root)
        profile_window.title("Edit Profile")
        profile_window.geometry("400x350")
        profile_window.configure(bg="#2c3e50")

        tk.Label(profile_window, text="👤 Edit Profile", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=15)

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
        self.current_user = None
        # Don't reset user_data to zeros - this preserves offline stats
        # When logging back in, server stats will overwrite these anyway
        self.show_welcome_screen()

    def start_solo_game(self):
        self.start_game(
            mode="solo",
            player_names=[self.display_name, "Bot"],
            player_avatars=[self.display_avatar, "🤖"],
            my_player_index=0
        )

    def host_multiplayer(self):
        if not self.websocket:
            threading.Thread(target=self._host_game_thread, daemon=True).start()
            self.show_waiting_dialog("Creating game session...")

    def join_multiplayer(self):
        invite_code = simpledialog.askstring("Join Game", "Enter invite code:")
        if invite_code and len(invite_code.strip()) == 8:
            threading.Thread(target=self._join_game_thread, args=(invite_code.strip(),), daemon=True).start()
            self.show_waiting_dialog(f"Joining game {invite_code.upper()}...")
        else:
            messagebox.showerror("Invalid Code", "Please enter a valid 8-character invite code")

    def show_waiting_dialog(self, message):
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
        if self.websocket:
            try:
                def close_websocket():
                    try:
                        if hasattr(self.websocket, 'close'):
                            asyncio.create_task(self.websocket.close())
                    except:
                        pass

                threading.Thread(target=close_websocket, daemon=True).start()
            except:
                pass
            self.websocket = None

        if hasattr(self, 'waiting_window'):
            self.waiting_window.destroy()

    def _host_game_thread(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._host_game_async())
        except Exception as e:
            print(f"Host game error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Connection Failed", "Failed to host game"))

    def _join_game_thread(self, invite_code):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._join_game_async(invite_code))
        except Exception as e:
            print(f"Join game error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Connection Failed", "Failed to join game"))

    async def _host_game_async(self):
        try:
            websocket_kwargs = {}

            connect_sig = inspect.signature(websockets.connect)
            if 'extra_headers' in connect_sig.parameters:
                websocket_kwargs['extra_headers'] = {
                    'User-Agent': 'SnakeLadderGame/1.0'
                }

            self.websocket = await websockets.connect(WEBSOCKET_SERVER, **websocket_kwargs)
            self.is_host = True

            await self.websocket.send(json.dumps({
                "type": "create_session",
                "player_name": self.display_name,
                "player_avatar": self.display_avatar
            }))

            await self._handle_websocket_messages()

        except Exception as e:
            print(f"Host async error: {e}")

    async def _join_game_async(self, invite_code):
        try:
            websocket_kwargs = {}

            connect_sig = inspect.signature(websockets.connect)
            if 'extra_headers' in connect_sig.parameters:
                websocket_kwargs['extra_headers'] = {
                    'User-Agent': 'SnakeLadderGame/1.0'
                }

            self.websocket = await websockets.connect(WEBSOCKET_SERVER, **websocket_kwargs)
            self.is_host = False

            await self.websocket.send(json.dumps({
                "type": "join_session",
                "invite_code": invite_code.upper(),
                "player_name": self.display_name,
                "player_avatar": self.display_avatar
            }))

            await self._handle_websocket_messages()

        except Exception as e:
            print(f"Join async error: {e}")

    async def _handle_websocket_messages(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._process_websocket_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
        except Exception as e:
            print(f"WebSocket message handling error: {e}")

    async def _process_websocket_message(self, data):
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
        if hasattr(self, 'waiting_window'):
            self.waiting_window.destroy()

        if not self.peer_info:
            messagebox.showerror("Error", "Peer information not available")
            return

        if self.is_host:
            player_names = [self.display_name, self.peer_info.get('name', 'Guest')]
            player_avatars = [self.display_avatar, self.peer_info.get('avatar', '😎')]
            my_player_index = 0
        else:
            player_names = [self.peer_info.get('name', 'Host'), self.display_name]
            player_avatars = [self.peer_info.get('avatar', '🙂'), self.display_avatar]
            my_player_index = 1

        self.start_game(
            mode="multiplayer",
            player_names=player_names,
            player_avatars=player_avatars,
            my_player_index=my_player_index
        )

    def start_game(self, mode, player_names, player_avatars, my_player_index=0):
        self.root.iconify()

        game_window = tk.Toplevel(self.root)
        game_window.title("Slide to Glory Game")
        game_window.lift()
        game_window.focus_force()

        try:
            self.game_instance = SnakeLadderGame(
                window=game_window,
                player_names=player_names,
                player_avatars=player_avatars,
                mode=mode,
                websocket_connection=WebSocketConnection(self.websocket,
                                                         self.session_id) if mode == "multiplayer" else None,
                is_host=self.is_host if mode == "multiplayer" else True,
                my_player_index=my_player_index,
                on_game_end=self.on_game_end
            )
        except Exception as e:
            messagebox.showerror("Game Error", f"Failed to start game: {e}")
            self.root.deiconify()

    def on_game_end(self, winner_idx, game_duration=None):
        self.root.deiconify()

        # Initialize is_winner as None (for when game is quit without a winner)
        is_winner = None

        if winner_idx is not None:
            # Determine if current player won
            if hasattr(self, 'is_host') and self.is_host:
                is_winner = (winner_idx == 0)
            elif hasattr(self.game_instance, 'my_player_index'):
                is_winner = (winner_idx == self.game_instance.my_player_index)
            else:
                # Fallback for solo mode
                is_winner = (winner_idx == 0)

            self.user_data["games_played"] = self.user_data.get("games_played", 0) + 1

            if is_winner:
                self.user_data["wins"] = self.user_data.get("wins", 0) + 1
                if game_duration:
                    fastest = self.user_data.get("fastest_win")
                    if fastest is None or game_duration < fastest:
                        self.user_data["fastest_win"] = game_duration
            else:
                self.user_data["losses"] = self.user_data.get("losses", 0) + 1

        # Save + Sync stats
        self.save_local_stats()
        if self.current_user and self.current_user != "offline":
            try:
                headers = {
                    'ngrok-skip-browser-warning': 'true',
                    'User-Agent': 'SnakeLadderGame/1.0',
                    'Content-Type': 'application/json'
                }
                self.http_session.post(
                    f"{AUTH_SERVER}/update_stats",
                    json={"username": self.current_user, "user_data": self.user_data},
                    headers=headers,
                    timeout=10
                )
            except Exception as e:
                print(f"Could not sync stats: {e}")

        # Reset WebSocket
        if self.websocket:
            try:
                def close_websocket_async():
                    try:
                        if hasattr(self.websocket, 'close'):
                            asyncio.create_task(self.websocket.close())
                    except:
                        pass

                threading.Thread(target=close_websocket_async, daemon=True).start()
            except:
                pass
            self.websocket = None

        self.session_id = None
        self.invite_code = None
        self.peer_info = None
        self.game_instance = None

        # Show Game Over window only if there was actually a winner
        if winner_idx is not None:
            self.show_game_over_window(is_winner, game_duration)
        else:
            # Just return to main menu if game was quit
            self.show_main_menu()

    def show_game_over_window(self, is_winner, game_duration=None):
        win_text = "🏆 You Win!" if is_winner else "😢 You Lost!"
        duration_text = ""
        if game_duration:
            minutes = int(game_duration // 60)
            seconds = int(game_duration % 60)
            duration_text = f"Game Duration: {minutes}m {seconds}s" if minutes > 0 else f"Game Duration: {seconds}s"

        game_over_win = tk.Toplevel(self.root)
        game_over_win.title("Game Over")
        game_over_win.geometry("400x300")
        game_over_win.configure(bg="#2c3e50")
        game_over_win.transient(self.root)
        game_over_win.grab_set()

        tk.Label(game_over_win, text=win_text, font=("Arial", 22, "bold"),
                 bg="#2c3e50", fg="#f1c40f").pack(pady=30)

        if duration_text:
            tk.Label(game_over_win, text=duration_text, font=("Arial", 14),
                     bg="#2c3e50", fg="white").pack(pady=10)

        button_frame = tk.Frame(game_over_win, bg="#2c3e50")
        button_frame.pack(pady=30)

        def back_to_menu():
            game_over_win.destroy()
            self.show_main_menu()

        def play_again():
            game_over_win.destroy()
            self.start_solo_game()

        tk.Button(button_frame, text="🔁 Play Again", font=("Arial", 14, "bold"),
                  bg="#27ae60", fg="white", padx=20, pady=10,
                  command=play_again).pack(side=tk.LEFT, padx=10)

        tk.Button(button_frame, text="🏠 Main Menu", font=("Arial", 14, "bold"),
                  bg="#e74c3c", fg="white", padx=20, pady=10,
                  command=back_to_menu).pack(side=tk.LEFT, padx=10)

    def run(self):
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            print(f"Application error: {e}")
        finally:
            if self.websocket:
                try:
                    def close_websocket_async():
                        try:
                            if hasattr(self.websocket, 'close'):
                                asyncio.create_task(self.websocket.close())
                        except:
                            pass

                    threading.Thread(target=close_websocket_async, daemon=True).start()
                except:
                    pass

    def on_closing(self):
        if self.websocket:
            try:
                def close_websocket_async():
                    try:
                        if hasattr(self.websocket, 'close'):
                            asyncio.create_task(self.websocket.close())
                    except:
                        pass

                threading.Thread(target=close_websocket_async, daemon=True).start()
            except:
                pass
        self.root.destroy()


class WebSocketConnection:
    def __init__(self, websocket, session_id):
        self.websocket = websocket
        self.session_id = session_id

    def send_message(self, data):
        if not self.websocket:
            print("No websocket connection available")
            return False

        try:
            message = {
                "type": "game_message",
                "session_id": self.session_id,
                "data": data
            }

            print(f"Sending message: {data}")

            def send_async():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    async def do_send():
                        await self.websocket.send(json.dumps(message))

                    loop.run_until_complete(do_send())
                    loop.close()

                except Exception as e:
                    print(f"Error in async send: {e}")

            send_thread = threading.Thread(target=send_async, daemon=True)
            send_thread.start()
            send_thread.join(timeout=5.0)

            return True

        except Exception as e:
            print(f"Error sending message: {e}")
            return False


if __name__ == "__main__":
    client = GameClient()
    client.run()