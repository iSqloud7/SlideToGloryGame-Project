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
from stats import StatsManager, sync_stats_with_server

# Try to import Music system
try:
    from music_manager import initialize_music, play_background_music, pause_music, resume_music, stop_music, \
        toggle_music, set_volume, get_music_info

    MUSIC_AVAILABLE = True
except ImportError:
    print("Music system not available - music_manager.py not found")
    MUSIC_AVAILABLE = False

# Localhost (vs Bot, on two terminals in one machine)
# AUTH_SERVER = "http://localhost:8000"
# WEBSOCKET_SERVER = "ws://localhost:8765"

# Internet (player1 vs player2)
AUTH_SERVER = "https://0abeb0f456d9.ngrok-free.app/"
WEBSOCKET_SERVER = "wss://4a094aa5a874.ngrok-free.app"


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
        self.display_name = "Player"
        self.display_avatar = "🙂"

        # Initialize stats manager (will be None until user logs in/plays offline)
        self.stats_manager = None

        self.websocket = None
        self.session_id = None
        self.invite_code = None
        self.is_host = False
        self.peer_info = None
        self.game_instance = None

        self.http_session = self.create_http_session()

        # Music system initialization
        self.music_initialized = False
        self.music_manager = None

        # Load local profile
        self.load_local_profile()

        self.check_servers()

        # Initialize Music after server check
        self.setup_music_controls()

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

    def save_local_profile(self):
        try:
            with open("profile.json", "w") as f:
                json.dump({
                    "name": self.display_name,
                    "avatar": self.display_avatar
                }, f)
        except:
            pass

    def setup_music_controls(self):
        """Initialize Music system and setup controls"""
        if not MUSIC_AVAILABLE:
            print("Music system not available")
            return

        try:
            self.music_manager = initialize_music()
            self.music_initialized = True
            print(f"Music system initialized: {self.music_manager.audio_system}")

            # Start background Music if available
            if self.music_manager.music_tracks:
                play_background_music()
                print(f"Started background Music - {len(self.music_manager.music_tracks)} tracks available")
            else:
                print("No Music files found. Add Music files to the 'Music' directory.")
        except Exception as e:
            print(f"Failed to initialize Music: {e}")
            self.music_initialized = False

    def add_music_controls_to_frame(self, parent_frame):
        """Add Music controls to a specific frame"""
        if not self.music_initialized:
            return

        # Music controls frame
        music_frame = tk.Frame(parent_frame, bg="#34495e", relief=tk.RAISED, bd=2)
        music_frame.pack(fill="both", expand=True)

        tk.Label(music_frame, text="🎵 Music Controls", font=("Arial", 14, "bold"),
                 bg="#34495e", fg="white").pack(pady=8)

        # Current track info
        self.music_info_label = tk.Label(music_frame, text="Loading...",
                                         font=("Arial", 10),
                                         bg="#34495e", fg="#bdc3c7",
                                         wraplength=200)
        self.music_info_label.pack(pady=5)

        # Control buttons frame
        controls_frame = tk.Frame(music_frame, bg="#34495e")
        controls_frame.pack(pady=8)

        # Row 1: Playback controls
        playback_frame = tk.Frame(controls_frame, bg="#34495e")
        playback_frame.pack(pady=2)

        self.prev_button = tk.Button(playback_frame, text="⏮️", command=self.previous_track,
                                     font=("Arial", 12), bg="#3498db", fg="white",
                                     width=3, padx=5)
        self.prev_button.pack(side=tk.LEFT, padx=2)

        self.play_pause_button = tk.Button(playback_frame, text="⏸️", command=self.toggle_play_pause,
                                           font=("Arial", 12), bg="#27ae60", fg="white",
                                           width=3, padx=5)
        self.play_pause_button.pack(side=tk.LEFT, padx=2)

        self.stop_button = tk.Button(playback_frame, text="⏹️", command=self.stop_music_action,
                                     font=("Arial", 12), bg="#e74c3c", fg="white",
                                     width=3, padx=5)
        self.stop_button.pack(side=tk.LEFT, padx=2)

        self.next_button = tk.Button(playback_frame, text="⏭️", command=self.next_track,
                                     font=("Arial", 12), bg="#3498db", fg="white",
                                     width=3, padx=5)
        self.next_button.pack(side=tk.LEFT, padx=2)

        # Row 2: Volume control
        volume_frame = tk.Frame(controls_frame, bg="#34495e")
        volume_frame.pack(pady=5)

        tk.Label(volume_frame, text="Volume:", font=("Arial", 10),
                 bg="#34495e", fg="white").pack(side=tk.LEFT)

        self.volume_scale = tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                     length=120, bg="#34495e", fg="white",
                                     highlightbackground="#34495e",
                                     command=self.on_volume_change)
        if self.music_manager:
            self.volume_scale.set(int(self.music_manager.volume * 100))
        self.volume_scale.pack(side=tk.LEFT, padx=5)

        # Row 3: Options
        options_frame = tk.Frame(controls_frame, bg="#34495e")
        options_frame.pack(pady=5)

        self.music_toggle_button = tk.Button(options_frame, text="🎵 ON", command=self.toggle_music_action,
                                             font=("Arial", 10), bg="#9b59b6", fg="white",
                                             width=8)
        self.music_toggle_button.pack(side=tk.LEFT, padx=2)

        self.playlist_button = tk.Button(options_frame, text="📋 Playlist", command=self.show_playlist,
                                         font=("Arial", 10), bg="#f39c12", fg="white",
                                         width=8)
        self.playlist_button.pack(side=tk.LEFT, padx=2)

        # Start updating Music info
        self.update_music_info()

    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if not self.music_initialized:
            return

        info = get_music_info()
        if info['status'] == 'playing':
            if pause_music():
                self.play_pause_button.config(text="▶️")
            else:
                # If pause failed, try to resume instead
                resume_music()
        elif info['status'] == 'paused':
            if resume_music():
                self.play_pause_button.config(text="⏸️")
        elif info['status'] == 'stopped':
            if play_background_music():
                self.play_pause_button.config(text="⏸️")

    def stop_music_action(self):
        """Stop Music playback"""
        if not self.music_initialized:
            return

        stop_music()
        if hasattr(self, 'play_pause_button'):
            self.play_pause_button.config(text="▶️")

    def next_track(self):
        """Skip to next track"""
        if not self.music_initialized:
            return

        if self.music_manager:
            self.music_manager.next_track()
            if hasattr(self, 'play_pause_button'):
                self.play_pause_button.config(text="⏸️")

    def previous_track(self):
        """Go to previous track"""
        if not self.music_initialized:
            return

        if self.music_manager:
            self.music_manager.previous_track()
            if hasattr(self, 'play_pause_button'):
                self.play_pause_button.config(text="⏸️")

    def on_volume_change(self, volume_str):
        """Handle volume slider change"""
        if not self.music_initialized:
            return

        try:
            volume = float(volume_str) / 100.0
            set_volume(volume)
        except:
            pass

    def toggle_music_action(self):
        """Toggle Music on/off"""
        if not self.music_initialized:
            return

        enabled = toggle_music()
        if hasattr(self, 'music_toggle_button'):
            self.music_toggle_button.config(text="🎵 ON" if enabled else "🎵 OFF",
                                            bg="#9b59b6" if enabled else "#95a5a6")

    def show_playlist(self):
        """Show the Music playlist window"""
        if not self.music_initialized:
            return

        playlist_window = tk.Toplevel(self.root)
        playlist_window.title("Music Playlist")
        playlist_window.geometry("500x400")
        playlist_window.configure(bg="#2c3e50")
        playlist_window.transient(self.root)

        # Header
        tk.Label(playlist_window, text="🎵 Music Playlist", font=("Arial", 16, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=15)

        # Playlist frame
        list_frame = tk.Frame(playlist_window, bg="#34495e", relief=tk.SUNKEN, bd=2)
        list_frame.pack(expand=True, fill="both", padx=20, pady=10)

        # Scrollable listbox
        scroll_frame = tk.Frame(list_frame)
        scroll_frame.pack(expand=True, fill="both", padx=10, pady=10)

        scrollbar = tk.Scrollbar(scroll_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.playlist_listbox = tk.Listbox(scroll_frame, yscrollcommand=scrollbar.set,
                                           bg="#2c3e50", fg="white", font=("Arial", 11),
                                           selectbackground="#3498db")
        self.playlist_listbox.pack(side=tk.LEFT, expand=True, fill="both")
        scrollbar.config(command=self.playlist_listbox.yview)

        # Populate playlist
        if self.music_manager:
            playlist = self.music_manager.get_playlist()
            for i, track in enumerate(playlist):
                self.playlist_listbox.insert(tk.END, f"{i + 1}. {track}")

        # Control buttons
        button_frame = tk.Frame(playlist_window, bg="#2c3e50")
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="▶️ Play Selected", command=lambda: self.play_selected_track(),
                  font=("Arial", 12), bg="#27ae60", fg="white",
                  padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="🔄 Refresh", command=lambda: self.refresh_playlist(),
                  font=("Arial", 12), bg="#3498db", fg="white",
                  padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="Close", command=playlist_window.destroy,
                  font=("Arial", 12), bg="#e74c3c", fg="white",
                  padx=15, pady=5).pack(side=tk.LEFT, padx=5)

    def play_selected_track(self):
        """Play the selected track from playlist"""
        if not hasattr(self, 'playlist_listbox'):
            return

        selection = self.playlist_listbox.curselection()
        if selection and self.music_manager:
            track_index = selection[0]
            if track_index < len(self.music_manager.music_tracks):
                track_path = self.music_manager.music_tracks[track_index]
                self.music_manager.play_music(track_path)
                if hasattr(self, 'play_pause_button'):
                    self.play_pause_button.config(text="⏸️")

    def refresh_playlist(self):
        """Refresh the Music playlist"""
        if self.music_manager:
            self.music_manager.scan_music_directory()
            if hasattr(self, 'playlist_listbox'):
                self.playlist_listbox.delete(0, tk.END)
                playlist = self.music_manager.get_playlist()
                for i, track in enumerate(playlist):
                    self.playlist_listbox.insert(tk.END, f"{i + 1}. {track}")

    def update_music_info(self):
        """Update the Music information display"""
        if not self.music_initialized:
            return

        try:
            info = get_music_info()

            if hasattr(self, 'music_info_label'):
                status_text = f"♪ {info['title']} - {info['status'].title()}"
                if 'track_number' in info and 'total_tracks' in info:
                    status_text += f" ({info['track_number']}/{info['total_tracks']})"

                self.music_info_label.config(text=status_text)

            # Update play/pause button
            if hasattr(self, 'play_pause_button'):
                if info['status'] == 'playing':
                    self.play_pause_button.config(text="⏸️")
                else:
                    self.play_pause_button.config(text="▶️")

        except Exception as e:
            if hasattr(self, 'music_info_label'):
                self.music_info_label.config(text="Music info unavailable")

        # Schedule next update
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.after(2000, self.update_music_info)  # Update every 2 seconds

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
            self.stats_manager = StatsManager("offline_player")
            self.show_main_menu(offline=True)
        else:
            messagebox.showerror(
                "Servers Offline",
                f"Both servers are offline.\n\nChecked URLs:\nAuth: {AUTH_SERVER}\nWebSocket: {WEBSOCKET_SERVER}\n\nOnly solo play available."
            )
            self.current_user = "offline"
            self.stats_manager = StatsManager("offline_player")
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

                    # Initialize stats manager for this user
                    self.stats_manager = StatsManager(self.current_user)

                    # Smart merging of server and local stats
                    server_user_data = result.get("user_data", {})
                    print(f"Server returned user_data: {server_user_data}")

                    if server_user_data:
                        # Sync with server stats
                        merged_stats = sync_stats_with_server(self.stats_manager, server_user_data)
                        print(f"Stats after smart merge: {merged_stats}")

                        # If local stats were higher, sync them back to server
                        if self.needs_server_sync(server_user_data, merged_stats):
                            print("Local stats were higher, syncing to server...")
                            self.sync_stats_to_server(merged_stats)
                    else:
                        # Server has no user_data, keep local stats and upload them
                        print("Server has no user data, keeping local stats")
                        global_stats = self.stats_manager.get_global_stats()
                        if any(global_stats.get(key, 0) > 0 for key in ["games_played", "wins", "losses"]):
                            print("Uploading local stats to server...")
                            self.sync_stats_to_server(global_stats)

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

        # Initialize stats manager for offline play
        self.stats_manager = StatsManager("offline_player")

        messagebox.showinfo("Offline Mode", "Playing in offline mode. Online features disabled.")
        self.show_main_menu(offline=True)

    def show_main_menu(self, offline=False, solo_only=False):
        self.clear_window()
        self.root.geometry("1000x900")  # Made even wider and taller to ensure everything fits
        self.root.title(f"Snake & Ladder - {self.display_name}")

        # Main container with scrollable content if needed
        main_container = tk.Frame(self.root, bg="#2c3e50")
        main_container.pack(expand=True, fill="both")

        # Header
        header = tk.Frame(main_container, bg="#34495e", height=100)
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

        # Content with proper spacing
        content = tk.Frame(main_container, bg="#2c3e50", padx=20, pady=20)
        content.pack(expand=True, fill="both")

        # Main game buttons section (centered at top)
        main_buttons_frame = tk.Frame(content, bg="#2c3e50")
        main_buttons_frame.pack(pady=(0, 20))

        tk.Label(main_buttons_frame, text="Choose Game Mode", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=(0, 15))

        tk.Button(main_buttons_frame, text="🎮 Play Solo (vs Bot)", font=("Arial", 16, "bold"),
                  command=self.start_solo_game, bg="#e74c3c", fg="white",
                  padx=25, pady=12, width=25).pack(pady=5)

        if not solo_only:
            tk.Button(main_buttons_frame, text="🌐 Host Multiplayer Game", font=("Arial", 16, "bold"),
                      command=self.host_multiplayer, bg="#27ae60", fg="white",
                      padx=25, pady=12, width=25).pack(pady=5)

            tk.Button(main_buttons_frame, text="🔗 Join Multiplayer Game", font=("Arial", 16, "bold"),
                      command=self.join_multiplayer, bg="#3498db", fg="white",
                      padx=25, pady=12, width=25).pack(pady=5)

        # Side-by-side layout for Music and stats with fixed height
        side_by_side_frame = tk.Frame(content, bg="#2c3e50", height=250)
        side_by_side_frame.pack(fill="x", pady=(0, 20))
        side_by_side_frame.pack_propagate(False)

        # Left side - Music controls
        music_container = tk.Frame(side_by_side_frame, bg="#2c3e50")
        music_container.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 10))

        if self.music_initialized:
            self.add_music_controls_to_frame(music_container)
        else:
            # Show placeholder if Music not available
            placeholder = tk.Frame(music_container, bg="#34495e", relief=tk.RAISED, bd=2)
            placeholder.pack(fill="both", expand=True)
            tk.Label(placeholder, text="🎵 Music Controls", font=("Arial", 14, "bold"),
                     bg="#34495e", fg="white").pack(pady=20)
            tk.Label(placeholder, text="Music system not available", font=("Arial", 10),
                     bg="#34495e", fg="#bdc3c7").pack()

        # Right side - Stats
        stats_container = tk.Frame(side_by_side_frame, bg="#2c3e50")
        stats_container.pack(side=tk.RIGHT, fill="both", expand=True, padx=(10, 0))

        if self.stats_manager:
            self.show_user_stats_in_frame(stats_container)
        else:
            # Show placeholder if stats not available
            placeholder = tk.Frame(stats_container, bg="#34495e", relief=tk.RAISED, bd=2)
            placeholder.pack(fill="both", expand=True)
            tk.Label(placeholder, text="📊 Statistics", font=("Arial", 14, "bold"),
                     bg="#34495e", fg="white").pack(pady=20)
            tk.Label(placeholder, text="No statistics available", font=("Arial", 10),
                     bg="#34495e", fg="#bdc3c7").pack()

        # BUTTONS SECTION - Three buttons in one row, centered
        buttons_container = tk.Frame(content, bg="#2c3e50")
        buttons_container.pack(fill="x", pady=(0, 20))

        # Add a separator line for visual clarity
        separator = tk.Frame(buttons_container, bg="#7f8c8d", height=1)
        separator.pack(fill="x", pady=(0, 15))

        tk.Label(buttons_container, text="Options & Tools", font=("Arial", 14, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=(0, 10))

        # Single row with three buttons - using simple pack with side=LEFT
        button_row = tk.Frame(buttons_container, bg="#2c3e50")
        button_row.pack()

        tk.Button(button_row, text="👤 Edit Profile", command=self.show_profile,
                  font=("Arial", 12, "bold"), bg="#9b59b6", fg="white",
                  padx=15, pady=8, width=20).pack(side=tk.LEFT, padx=5)

        tk.Button(button_row, text="📊 Detailed Stats", command=self.show_detailed_stats,
                  font=("Arial", 12, "bold"), bg="#3498db", fg="white",
                  padx=15, pady=8, width=20).pack(side=tk.LEFT, padx=5)

        if not offline and not solo_only:
            tk.Button(button_row, text="🏆 Leaderboard", command=self.show_leaderboard,
                      font=("Arial", 12, "bold"), bg="#f39c12", fg="white",
                      padx=15, pady=8, width=20).pack(side=tk.LEFT, padx=5)
        else:
            tk.Button(button_row, text="🏆 Leaderboard",
                      command=lambda: messagebox.showinfo("Offline Mode", "Leaderboard requires online connection."),
                      font=("Arial", 12, "bold"), bg="#95a5a6", fg="white",
                      padx=15, pady=8, width=20).pack(side=tk.LEFT, padx=5)

        # Second row of buttons
        bottom_buttons = tk.Frame(buttons_container, bg="#2c3e50")
        bottom_buttons.pack(pady=(15, 0))

        if not offline:
            tk.Button(bottom_buttons, text="🚪 Logout", command=self.logout,
                      font=("Arial", 12, "bold"), bg="#e67e22", fg="white",
                      padx=20, pady=10, width=30).pack()
        else:
            tk.Button(bottom_buttons, text="🔄 Reset Session", command=self.reset_current_session,
                      font=("Arial", 12, "bold"), bg="#f39c12", fg="white",
                      padx=20, pady=10, width=30).pack()

    def show_user_stats_in_frame(self, parent_frame):
        """Show user statistics in a specific frame"""
        if not self.stats_manager:
            return

        stats_frame = tk.Frame(parent_frame, bg="#34495e", relief=tk.RAISED, bd=2)
        stats_frame.pack(fill="both", expand=True)

        tk.Label(stats_frame, text="📊 Your Statistics", font=("Arial", 14, "bold"),
                 bg="#34495e", fg="white").pack(pady=8)

        # Create tabs for Local vs Global stats
        tab_frame = tk.Frame(stats_frame, bg="#34495e")
        tab_frame.pack(pady=5)

        # Tab buttons
        self.current_tab = tk.StringVar(value="session")

        tk.Radiobutton(tab_frame, text="Current Session", variable=self.current_tab,
                       value="session", command=lambda: self.update_stats_display_in_frame(stats_frame),
                       bg="#34495e", fg="white", font=("Arial", 10, "bold"),
                       selectcolor="#3498db").pack(side=tk.LEFT, padx=5)

        tk.Radiobutton(tab_frame, text="All Time", variable=self.current_tab,
                       value="global", command=lambda: self.update_stats_display_in_frame(stats_frame),
                       bg="#34495e", fg="white", font=("Arial", 10, "bold"),
                       selectcolor="#3498db").pack(side=tk.LEFT, padx=5)

        # Stats display area
        self.stats_display_frame = tk.Frame(stats_frame, bg="#34495e")
        self.stats_display_frame.pack(pady=5, fill="both", expand=True)

        self.update_stats_display_in_frame(stats_frame)

    def update_stats_display_in_frame(self, parent_frame):
        """Update the statistics display based on current tab in a specific frame"""
        # Clear existing display
        for widget in self.stats_display_frame.winfo_children():
            widget.destroy()

        if not self.stats_manager:
            return

        display_stats = self.stats_manager.get_display_stats()

        if self.current_tab.get() == "session":
            # Show session stats
            session_stats = [
                ("Progress", display_stats["session_progress"]),
                ("Games", display_stats["session_games"]),
                ("Win Rate", display_stats["session_win_rate"])
            ]

            tk.Label(self.stats_display_frame, text="Current Session",
                     font=("Arial", 11, "bold"), bg="#34495e", fg="#f1c40f").pack(pady=2)

            for label, value in session_stats:
                tk.Label(self.stats_display_frame, text=f"{label}: {value}",
                         font=("Arial", 10), bg="#34495e", fg="#27ae60").pack(pady=1, anchor="w", padx=10)

            # Show session completion status
            local_stats = self.stats_manager.get_local_stats()
            if local_stats["session_complete"]:
                tk.Label(self.stats_display_frame, text="🏆 Session Complete!\nStarting new session...",
                         font=("Arial", 9, "italic"), bg="#34495e", fg="#f39c12",
                         justify=tk.CENTER).pack(pady=2)

        else:
            # Show global stats
            global_stats = [
                ("Total Games", display_stats["total_games"]),
                ("Wins/Losses", f"{display_stats['total_wins']}/{display_stats['total_losses']}"),
                ("Win Rate", display_stats["overall_win_rate"]),
                ("Best Streak", display_stats["best_win_streak"]),
                ("Fastest Win", display_stats["fastest_win"])
            ]

            tk.Label(self.stats_display_frame, text="All-Time Statistics",
                     font=("Arial", 11, "bold"), bg="#34495e", fg="#f1c40f").pack(pady=2)

            for label, value in global_stats:
                tk.Label(self.stats_display_frame, text=f"{label}: {value}",
                         font=("Arial", 10), bg="#34495e", fg="#27ae60").pack(pady=1, anchor="w", padx=10)

    def show_detailed_stats(self):
        """Show a detailed statistics window"""
        if not self.stats_manager:
            messagebox.showinfo("No Stats", "No statistics available yet.")
            return

        stats_window = tk.Toplevel(self.root)
        stats_window.title("Detailed Statistics")
        stats_window.geometry("600x500")
        stats_window.configure(bg="#2c3e50")
        stats_window.transient(self.root)

        # Header
        tk.Label(stats_window, text="📊 Detailed Statistics",
                 font=("Arial", 18, "bold"), bg="#2c3e50", fg="white").pack(pady=15)

        # Create notebook for tabs
        notebook_frame = tk.Frame(stats_window, bg="#2c3e50")
        notebook_frame.pack(expand=True, fill="both", padx=20, pady=10)

        # Session stats
        session_frame = tk.LabelFrame(notebook_frame, text="Current Session",
                                      font=("Arial", 12, "bold"), bg="#34495e", fg="white")
        session_frame.pack(fill="x", pady=5)

        display_stats = self.stats_manager.get_display_stats()
        local_stats = self.stats_manager.get_local_stats()

        session_info = [
            f"Progress: {display_stats['session_progress']}",
            f"Games Played: {display_stats['session_games']}",
            f"Win Rate: {display_stats['session_win_rate']}",
            f"Session Started: {local_stats.get('session_start', 'N/A')[:19] if local_stats.get('session_start') else 'N/A'}"
        ]

        for info in session_info:
            tk.Label(session_frame, text=info, font=("Arial", 10),
                     bg="#34495e", fg="#bdc3c7").pack(anchor="w", padx=10, pady=2)

        # Global stats
        global_frame = tk.LabelFrame(notebook_frame, text="All-Time Statistics",
                                     font=("Arial", 12, "bold"), bg="#34495e", fg="white")
        global_frame.pack(fill="x", pady=5)

        global_info = [
            f"Total Games: {display_stats['total_games']}",
            f"Wins: {display_stats['total_wins']} | Losses: {display_stats['total_losses']}",
            f"Overall Win Rate: {display_stats['overall_win_rate']}",
            f"Current Win Streak: {display_stats['current_win_streak']}",
            f"Best Win Streak: {display_stats['best_win_streak']}",
            f"Fastest Win: {display_stats['fastest_win']}",
            f"Longest Game: {display_stats['longest_game']}",
            f"Total Playtime: {display_stats['total_playtime']}"
        ]

        for info in global_info:
            tk.Label(global_frame, text=info, font=("Arial", 10),
                     bg="#34495e", fg="#bdc3c7").pack(anchor="w", padx=10, pady=2)

        # Buttons
        button_frame = tk.Frame(stats_window, bg="#2c3e50")
        button_frame.pack(pady=15)

        tk.Button(button_frame, text="Reset Session",
                  command=self.reset_current_session,
                  font=("Arial", 12), bg="#e67e22", fg="white",
                  padx=15, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="Close", command=stats_window.destroy,
                  font=("Arial", 12), bg="#95a5a6", fg="white",
                  padx=20, pady=5).pack(side=tk.RIGHT, padx=5)

    def reset_current_session(self):
        """Reset the current session after confirmation"""
        if not self.stats_manager:
            return

        result = messagebox.askyesno("Reset Session",
                                     "Are you sure you want to reset your current session? This will start a new session from 0 wins.")
        if result:
            self.stats_manager.reset_session()
            messagebox.showinfo("Session Reset", "Your session has been reset. Good luck!")
            # Refresh the main menu to show updated stats
            self.show_main_menu()

    def show_leaderboard(self):
        """Show the global leaderboard"""
        if self.current_user == "offline":
            messagebox.showinfo("Offline Mode", "Leaderboard is not available in offline mode.")
            return

        # Create leaderboard window
        leaderboard_window = tk.Toplevel(self.root)
        leaderboard_window.title("Global Leaderboard")
        leaderboard_window.geometry("800x600")
        leaderboard_window.configure(bg="#2c3e50")
        leaderboard_window.transient(self.root)

        # Header
        header_frame = tk.Frame(leaderboard_window, bg="#34495e", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="🏆 Global Leaderboard",
                 font=("Arial", 20, "bold"), bg="#34495e", fg="white").pack(pady=20)

        # Loading label
        loading_label = tk.Label(leaderboard_window, text="Loading leaderboard...",
                                 font=("Arial", 14), bg="#2c3e50", fg="white")
        loading_label.pack(pady=50)

        # Fetch leaderboard data in background
        def fetch_leaderboard():
            try:
                headers = {
                    'ngrok-skip-browser-warning': 'true',
                    'User-Agent': 'SnakeLadderGame/1.0'
                }
                response = self.http_session.get(f"{AUTH_SERVER}/leaderboard",
                                                 timeout=10, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    self.root.after(0, lambda: self.display_leaderboard(leaderboard_window,
                                                                        loading_label, data))
                else:
                    self.root.after(0, lambda: self.show_leaderboard_error(loading_label,
                                                                           "Failed to fetch leaderboard"))
            except Exception as e:
                error_msg = f"Error loading leaderboard: {str(e)}"
                self.root.after(0, lambda: self.show_leaderboard_error(loading_label, error_msg))

        # Start background fetch
        import threading
        threading.Thread(target=fetch_leaderboard, daemon=True).start()

    def display_leaderboard(self, window, loading_label, data):
        """Display the leaderboard data"""
        loading_label.destroy()

        leaderboard = data.get("leaderboard", [])
        total_players = data.get("total_players", 0)

        if not leaderboard:
            tk.Label(window, text="No players found on leaderboard.",
                     font=("Arial", 14), bg="#2c3e50", fg="white").pack(pady=50)
            return

        # Info frame
        info_frame = tk.Frame(window, bg="#34495e")
        info_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(info_frame, text=f"Showing top {len(leaderboard)} of {total_players} players",
                 font=("Arial", 12), bg="#34495e", fg="#bdc3c7").pack()

        # Create scrollable frame
        canvas_frame = tk.Frame(window, bg="#2c3e50")
        canvas_frame.pack(expand=True, fill="both", padx=20, pady=10)

        canvas = tk.Canvas(canvas_frame, bg="#2c3e50", highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2c3e50")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Header row
        header_frame = tk.Frame(scrollable_frame, bg="#34495e", relief=tk.RAISED, bd=2)
        header_frame.pack(fill="x", pady=(0, 5))

        headers = ["Rank", "Player", "Games", "Wins", "Win Rate", "Best Streak", "Fastest Win"]
        header_widths = [8, 15, 8, 8, 10, 12, 12]

        for i, (header, width) in enumerate(zip(headers, header_widths)):
            tk.Label(header_frame, text=header, font=("Arial", 11, "bold"),
                     bg="#34495e", fg="white", width=width).grid(row=0, column=i, padx=2, pady=5)

        # Player rows
        for rank, player in enumerate(leaderboard, 1):
            # Highlight current user
            bg_color = "#3498db" if player["username"].lower() == self.current_user.lower() else "#2c3e50"
            text_color = "white" if player["username"].lower() == self.current_user.lower() else "#bdc3c7"

            player_frame = tk.Frame(scrollable_frame, bg=bg_color, relief=tk.RAISED, bd=1)
            player_frame.pack(fill="x", pady=1)

            # Format fastest win
            fastest_win = player.get("fastest_win")
            if fastest_win:
                if fastest_win < 60:
                    fastest_win_str = f"{fastest_win}s"
                else:
                    minutes = fastest_win // 60
                    seconds = fastest_win % 60
                    fastest_win_str = f"{minutes}m {seconds}s"
            else:
                fastest_win_str = "N/A"

            values = [
                str(rank),
                player["username"][:13] + "..." if len(player["username"]) > 13 else player["username"],
                str(player["games_played"]),
                str(player["wins"]),
                f"{player['win_rate']}%",
                str(player["best_win_streak"]),
                fastest_win_str
            ]

            for i, (value, width) in enumerate(zip(values, header_widths)):
                font_weight = "bold" if bg_color == "#3498db" else "normal"
                tk.Label(player_frame, text=value, font=("Arial", 10, font_weight),
                         bg=bg_color, fg=text_color, width=width).grid(row=0, column=i, padx=2, pady=3)

        # Close button
        tk.Button(window, text="Close", command=window.destroy,
                  font=("Arial", 12), bg="#e74c3c", fg="white",
                  padx=20, pady=8).pack(pady=20)

    def show_leaderboard_error(self, loading_label, error_msg):
        """Show error message when leaderboard fails to load"""
        loading_label.config(text=error_msg, fg="#e74c3c")

        # Add retry button
        retry_frame = tk.Frame(loading_label.master, bg="#2c3e50")
        retry_frame.pack(pady=20)

        tk.Button(retry_frame, text="Retry", command=lambda: self.retry_leaderboard(loading_label.master),
                  font=("Arial", 12), bg="#3498db", fg="white", padx=20, pady=8).pack(side=tk.LEFT, padx=5)

        tk.Button(retry_frame, text="Close", command=loading_label.master.destroy,
                  font=("Arial", 12), bg="#e74c3c", fg="white", padx=20, pady=8).pack(side=tk.LEFT, padx=5)

    def retry_leaderboard(self, window):
        """Retry loading the leaderboard"""
        window.destroy()
        self.show_leaderboard()

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
        self.stats_manager = None
        self.show_welcome_screen()

    def needs_server_sync(self, server_stats, merged_stats):
        """Check if we need to sync stats back to server"""
        for key in ["games_played", "wins", "losses"]:
            if merged_stats.get(key, 0) > server_stats.get(key, 0):
                return True
        return False

    def sync_stats_to_server(self, stats_data):
        """Sync statistics to the server"""
        if not self.current_user or self.current_user == "offline":
            return

        try:
            headers = {
                'ngrok-skip-browser-warning': 'true',
                'User-Agent': 'SnakeLadderGame/1.0',
                'Content-Type': 'application/json'
            }

            response = self.http_session.post(
                f"{AUTH_SERVER}/update_stats",
                json={"username": self.current_user, "user_data": stats_data},
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                print("Successfully synced stats to server")
            else:
                print(f"Failed to sync stats: {response.status_code}")

        except Exception as e:
            print(f"Error syncing stats to server: {e}")

    def cleanup_multiplayer(self):
        """Clean up multiplayer connections"""
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

            # Record the game in statistics
            if self.stats_manager and game_duration:
                opponent = "Bot" if hasattr(self.game_instance,
                                            'mode') and self.game_instance.mode == 'solo' else "Player"
                self.stats_manager.record_game(is_winner, game_duration, opponent)

                # Sync to server if online
                if self.current_user and self.current_user != "offline":
                    self.sync_stats_to_server(self.stats_manager.get_global_stats())

        # Reset WebSocket and show results
        self.cleanup_multiplayer()

        if winner_idx is not None:
            self.show_game_over_window(is_winner, game_duration)
        else:
            self.show_main_menu()

    def show_game_over_window(self, is_winner, game_duration=None):
        """Show a beautiful game over dialog with winner announcement and options"""
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
            self.cleanup_multiplayer()
            if self.music_initialized and self.music_manager:
                self.music_manager.cleanup()

    def on_closing(self):
        if self.music_initialized and self.music_manager:
            self.music_manager.cleanup()
        self.cleanup_multiplayer()
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