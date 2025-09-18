#!/usr/bin/env python3
"""
snake_ladder_core.py

Complete Snake & Ladder game core with enhanced graphics and multiplayer hooks.

Constructor signature matches your client:
SnakeLadderGame(window=..., player_names=[...], player_avatars=[...],
                mode="solo"|"multiplayer", websocket_connection=None,
                is_host=True/False, on_game_end=None)
"""
import tkinter as tk
from tkinter import messagebox
import random
import json
import time
import os
import math

# Board constants
BOARD_SIZE = 640
TILE_SIZE = BOARD_SIZE // 10
BOARD_MARGIN = 40
ROWS = 10
COLS = 10
CELL_SIZE = TILE_SIZE

# Default snakes and ladders (you can adjust or import externally)
SNAKES = {98: 78, 95: 56, 87: 24, 62: 18, 54: 34, 16: 6}
LADDERS = {1: 38, 4: 14, 9: 21, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100}


class SnakeLadderGame:
    """Main game class for Snake & Ladder with enhanced graphics and multiplayer hooks"""

    def __init__(self, window, player_names=None, player_avatars=None, mode="solo",
                 websocket_connection=None, is_host=True, on_game_end=None):

        # Window and UI
        self.window = window
        self.window.title("Snake & Ladder Game")
        self.window.configure(bg="#2c3e50")

        # Players and mode
        self.player_names = player_names or ["Player 1", "Player 2"]
        self.player_avatars = player_avatars or ["🙂", "😎"]
        self.mode = mode  # "solo" or "multiplayer"
        self.websocket_connection = websocket_connection
        self.is_host = is_host
        self.on_game_end = on_game_end

        # Game state
        self.positions = [0, 0]  # player positions
        self.dice_value = 0
        self.current_player = 0  # 0 or 1
        self.game_over = False
        self.my_turn = self.is_host if mode == "multiplayer" else True

        # Animation / state flags
        self.moving = False
        self.dice_rolling = False

        # Stats
        self.start_time = time.time()
        self.move_count = [0, 0]

        # Store snakes and ladders for internal use
        self.snakes = SNAKES
        self.ladders = LADDERS

        # UI setup
        self.setup_ui()
        self.create_board()
        self.create_tokens()
        self.update_ui_state()

        # If multiplayer, start periodic check for network messages (non-blocking)
        if self.mode == "multiplayer":
            # The GameClient should pass a WebSocketConnection-like object that
            # exposes send_message(data) and the GameClient handles incoming messages
            # by calling this instance's handle_network_message method via game_message delivery.
            # But we keep a periodic check loop for any queued internal tasks if needed.
            self.window.after(200, self.check_network_messages)

    # ----- UI setup -----
    def setup_ui(self):
        """Setup main window layout and controls"""
        self.window.geometry("1000x750")
        self.window.resizable(False, False)

        main_frame = tk.Frame(self.window, bg="#2c3e50")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Board container
        board_container = tk.Frame(main_frame, bg="#34495e", relief=tk.RAISED, bd=3)
        board_container.pack(side=tk.LEFT, padx=5)

        canvas_size = BOARD_SIZE + BOARD_MARGIN * 2
        self.canvas = tk.Canvas(board_container,
                                width=canvas_size, height=canvas_size,
                                bg="#f4f1de", highlightbackground="#34495e")
        self.canvas.pack(padx=5, pady=5)

        # Controls container
        controls_frame = tk.Frame(main_frame, bg="#34495e", width=300, relief=tk.RAISED, bd=3)
        controls_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        controls_frame.pack_propagate(False)

        self.setup_controls(controls_frame)

    def setup_controls(self, parent):
        """Create control widgets on the right panel"""
        tk.Label(parent, text="Snake & Ladder", font=("Arial", 18, "bold"),
                 bg="#34495e", fg="white").pack(pady=15)

        players_frame = tk.Frame(parent, bg="#2c3e50", relief=tk.SUNKEN, bd=2)
        players_frame.pack(pady=10, padx=15, fill="x")

        self.player_labels = []
        colors = ["#e74c3c", "#3498db"]

        for i in range(2):
            avatar = self.player_avatars[i] if i < len(self.player_avatars) else ""
            name = self.player_names[i] if i < len(self.player_names) else f"Player {i + 1}"
            label = tk.Label(players_frame, text=f"{avatar} {name}",
                             font=("Arial", 12, "bold"),
                             bg="#2c3e50", fg=colors[i])
            label.pack(pady=3)
            self.player_labels.append(label)

        # Mode label
        mode_text = f"Mode: {self.mode.title()}"
        if self.mode == "multiplayer":
            role = "Host" if self.is_host else "Guest"
            mode_text += f" ({role})"

        tk.Label(parent, text=mode_text, font=("Arial", 10),
                 bg="#34495e", fg="#bdc3c7").pack(pady=5)

        # Dice area
        dice_frame = tk.Frame(parent, bg="#34495e")
        dice_frame.pack(pady=20)

        self.dice_label = tk.Label(dice_frame, text="🎲", font=("Arial", 50), bg="#34495e", fg="white")
        self.dice_label.pack(pady=10)

        self.roll_button = tk.Button(dice_frame, text="Roll Dice", command=self.roll_dice,
                                     font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                                     padx=20, pady=10, width=12)
        self.roll_button.pack(pady=5)

        # Status label
        self.status_label = tk.Label(parent, text="Game starting...", font=("Arial", 12, "bold"),
                                     bg="#34495e", fg="#f1c40f", wraplength=260, justify="center")
        self.status_label.pack(pady=15)

        controls_container = tk.Frame(parent, bg="#34495e")
        controls_container.pack(pady=10)

        tk.Button(controls_container, text="Reset Game", command=self.reset_game,
                  font=("Arial", 12), bg="#e67e22", fg="white", padx=15, pady=5, width=12).pack(pady=3)

        tk.Button(controls_container, text="Quit Game", command=self.quit_game,
                  font=("Arial", 12), bg="#c0392b", fg="white", padx=15, pady=5, width=12).pack(pady=3)

    # ----- Board drawing -----
    def create_board(self):
        """Create the game board with numbered squares"""
        # Draw the numbered squares first
        for square_num in range(1, 101):
            x, y = self.get_square_coords(square_num)

            # Checkerboard pattern
            row = (square_num - 1) // 10
            col = (square_num - 1) % 10
            if row % 2 == 1:  # Odd rows go right to left
                col = 9 - col

            if (row + col) % 2 == 0:
                fill_color = "#f8f9fa"
            else:
                fill_color = "#e9ecef"

            # Draw square
            self.canvas.create_rectangle(x, y, x + TILE_SIZE, y + TILE_SIZE,
                                         fill=fill_color, outline="#6c757d", width=1)

            # Draw number
            text_x = x + TILE_SIZE // 2
            text_y = y + TILE_SIZE // 2
            self.canvas.create_text(text_x, text_y, text=str(square_num),
                                    font=("Arial", 10, "bold"), fill="#495057")

        # Draw snakes and ladders after squares
        self.draw_enhanced_snakes_and_ladders()

    def get_square_coords(self, square_num):
        """Get top-left corner coordinates for a square number (1-100)"""
        if square_num <= 0 or square_num > 100:
            return 0, 0

        idx = square_num - 1
        row = idx // 10
        col = idx % 10

        # Snake and ladder boards go in serpentine pattern
        if row % 2 == 1:  # Odd rows (from bottom) go right to left
            col = 9 - col

        x = col * TILE_SIZE + BOARD_MARGIN
        y = BOARD_SIZE - ((row + 1) * TILE_SIZE) + BOARD_MARGIN

        return x, y

    def get_coords(self, square_num):
        """Get coordinates for drawing snakes and ladders (compatibility method)"""
        return self.get_square_coords(square_num)

    def draw_enhanced_snakes_and_ladders(self):
        """Draw realistic snakes and ladders"""
        for head, tail in SNAKES.items():
            self.draw_realistic_snake(head, tail)
        for bottom, top in LADDERS.items():
            self.draw_realistic_ladder(bottom, top)

    def get_square_center(self, square_num):
        """Return (x,y) center coords for square number (1..100)."""
        if square_num <= 0:
            # off-board starting positions (below board)
            return BOARD_MARGIN // 2, BOARD_SIZE + BOARD_MARGIN + BOARD_MARGIN // 2

        if square_num > 100:
            square_num = 100

        x, y = self.get_square_coords(square_num)
        center_x = x + TILE_SIZE // 2
        center_y = y + TILE_SIZE // 2

        return center_x, center_y

    # ---- snakes & ladders drawing ----
    def draw_realistic_snake(self, head_pos, tail_pos):
        """Draw a realistic curved snake"""
        head_x, head_y = self.get_square_center(head_pos)
        tail_x, tail_y = self.get_square_center(tail_pos)

        mid_x = (head_x + tail_x) / 2
        mid_y = (head_y + tail_y) / 2

        curve_offset = 30 + random.randint(-12, 12)
        if head_x < tail_x:
            curve_offset = -curve_offset

        control1_x = mid_x + curve_offset
        control1_y = mid_y - 30
        control2_x = mid_x - curve_offset
        control2_y = mid_y + 30

        segments = 10
        points = []
        for i in range(segments + 1):
            t = i / segments
            # cubic bezier formula
            x = (1 - t) ** 3 * head_x + 3 * (1 - t) ** 2 * t * control1_x + 3 * (
                        1 - t) * t ** 2 * control2_x + t ** 3 * tail_x
            y = (1 - t) ** 3 * head_y + 3 * (1 - t) ** 2 * t * control1_y + 3 * (
                        1 - t) * t ** 2 * control2_y + t ** 3 * tail_y
            points.extend([x, y])

        # body segments
        for i in range(0, len(points) - 4, 2):
            x1, y1 = points[i], points[i + 1]
            x2, y2 = points[i + 2], points[i + 3]
            width = max(6, 14 - (i // 2) * 0.6)
            intensity = 1.0 - (i / len(points))
            green_val = int(80 + intensity * 120)
            r = int(green_val * 0.2)
            g = min(255, green_val)
            b = int(green_val * 0.4)
            color = f"#{r:02x}{g:02x}{b:02x}"

            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=int(width), smooth=True, capstyle=tk.ROUND)

        # small scales
        for i in range(2, len(points) - 4, 4):
            x, y = points[i], points[i + 1]
            self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#2d5016", outline="")

        # head
        head_radius = 16
        self.canvas.create_oval(head_x - head_radius + 2, head_y - head_radius + 2,
                                head_x + head_radius + 2, head_y + head_radius + 2,
                                fill="#1a3d0a", outline="")
        self.canvas.create_oval(head_x - head_radius, head_y - head_radius,
                                head_x + head_radius, head_y + head_radius,
                                fill="#4a7c59", outline="#2d5016", width=2)

        # eyes
        for eye_x_offset in (-5, 5):
            self.canvas.create_oval(head_x + eye_x_offset - 3, head_y - 8,
                                    head_x + eye_x_offset + 3, head_y - 2,
                                    fill="white", outline="#2d5016")
            self.canvas.create_oval(head_x + eye_x_offset - 1, head_y - 6,
                                    head_x + eye_x_offset + 1, head_y - 4,
                                    fill="black", outline="")

        # tongue
        tongue_length = 12
        angle = math.atan2(control1_y - head_y, control1_x - head_x)
        tongue_x = head_x + math.cos(angle) * tongue_length
        tongue_y = head_y + math.sin(angle) * tongue_length
        self.canvas.create_line(head_x, head_y + 3, tongue_x, tongue_y, fill="#ff4444", width=2)
        fork_angle1 = angle - 0.28
        fork_angle2 = angle + 0.28
        fork_len = 6
        self.canvas.create_line(tongue_x, tongue_y,
                                tongue_x + math.cos(fork_angle1) * fork_len,
                                tongue_y + math.sin(fork_angle1) * fork_len,
                                fill="#ff4444", width=2)
        self.canvas.create_line(tongue_x, tongue_y,
                                tongue_x + math.cos(fork_angle2) * fork_len,
                                tongue_y + math.sin(fork_angle2) * fork_len,
                                fill="#ff4444", width=2)

    def draw_realistic_ladder(self, bottom_pos, top_pos):
        """Draw a realistic ladder with wooden texture"""
        bottom_x, bottom_y = self.get_square_center(bottom_pos)
        top_x, top_y = self.get_square_center(top_pos)

        rail_width = 8
        rail_offset = 14
        shadow_offset = 3

        # left rail shadow
        self.canvas.create_line(bottom_x - rail_offset + shadow_offset, bottom_y + shadow_offset,
                                top_x - rail_offset + shadow_offset, top_y + shadow_offset,
                                fill="#8b4513", width=rail_width, capstyle=tk.ROUND)
        # right rail shadow
        self.canvas.create_line(bottom_x + rail_offset + shadow_offset, bottom_y + shadow_offset,
                                top_x + rail_offset + shadow_offset, top_y + shadow_offset,
                                fill="#8b4513", width=rail_width, capstyle=tk.ROUND)

        # left rail
        self.canvas.create_line(bottom_x - rail_offset, bottom_y, top_x - rail_offset, top_y,
                                fill="#deb887", width=rail_width, capstyle=tk.ROUND)
        self.canvas.create_line(bottom_x - rail_offset - 2, bottom_y, top_x - rail_offset - 2, top_y,
                                fill="#f5deb3", width=2, capstyle=tk.ROUND)

        # right rail
        self.canvas.create_line(bottom_x + rail_offset, bottom_y, top_x + rail_offset, top_y,
                                fill="#deb887", width=rail_width, capstyle=tk.ROUND)
        self.canvas.create_line(bottom_x + rail_offset + 2, bottom_y, top_x + rail_offset + 2, top_y,
                                fill="#f5deb3", width=2, capstyle=tk.ROUND)

        ladder_height = abs(top_y - bottom_y)
        num_rungs = max(3, int(ladder_height / 25))
        for i in range(1, num_rungs):
            t = i / num_rungs
            rung_x = bottom_x + (top_x - bottom_x) * t
            rung_y = bottom_y + (top_y - bottom_y) * t

            # shadow
            self.canvas.create_line(rung_x - rail_offset + shadow_offset, rung_y + shadow_offset,
                                    rung_x + rail_offset + shadow_offset, rung_y + shadow_offset,
                                    fill="#8b4513", width=6, capstyle=tk.ROUND)
            # main rung
            self.canvas.create_line(rung_x - rail_offset, rung_y, rung_x + rail_offset, rung_y,
                                    fill="#cd853f", width=5, capstyle=tk.ROUND)
            # highlight
            self.canvas.create_line(rung_x - rail_offset, rung_y - 1, rung_x + rail_offset, rung_y - 1,
                                    fill="#f4a460", width=2, capstyle=tk.ROUND)

            # wood grain
            for grain in range(-8, 9, 4):
                if abs(grain) < rail_offset:
                    self.canvas.create_line(rung_x + grain, rung_y - 1, rung_x + grain, rung_y + 1,
                                            fill="#a0522d", width=1)

    # ----- tokens / players -----
    def create_tokens(self):
        """Create player tokens with animations"""
        self.tokens = []
        self.token_labels = []
        self.token_halos = []
        colors = ["#e74c3c", "#3498db"]

        for i in range(2):
            halo = self.canvas.create_oval(0, 0, 28, 28, fill="", outline=colors[i], width=3, tags=f"halo{i}")
            self.token_halos.append(halo)

            token = self.canvas.create_oval(0, 0, 24, 24, fill=colors[i], outline="white", width=3, tags=f"player{i}")
            self.tokens.append(token)

            highlight = self.canvas.create_oval(0, 0, 18, 18, fill="", outline="#ffffff", width=2, tags=f"highlight{i}")

            label = self.canvas.create_text(0, 0, text=self.player_avatars[i] if i < len(self.player_avatars) else "",
                                            font=("Arial", 16, "bold"), fill="white", tags=f"label{i}")
            self.token_labels.append(label)

            # Bind clicks: in solo allow both tokens; in multiplayer only allow local player's token
            if self.mode == "solo":
                self.canvas.tag_bind(f"player{i}", "<Button-1>", lambda e, p=i: self.try_move_token(p))
            else:
                allowed = (self.is_host and i == 0) or (not self.is_host and i == 1)
                if allowed:
                    self.canvas.tag_bind(f"player{i}", "<Button-1>", lambda e, p=i: self.try_move_token(p))

        self.update_token_positions()

    def update_token_positions(self):
        """Update visual positions of player tokens"""
        for i in range(2):
            if self.positions[i] <= 0:
                # place tokens off-board to the left and right start spots
                if i == 0:
                    x, y = BOARD_MARGIN // 2, BOARD_SIZE + BOARD_MARGIN + 15
                else:
                    x, y = BOARD_SIZE + BOARD_MARGIN + BOARD_MARGIN // 2, BOARD_SIZE + BOARD_MARGIN + 15
            else:
                x, y = self.get_square_center(self.positions[i])
                if i == 0:
                    x -= 12
                    y -= 12
                else:
                    x += 12
                    y += 12

            self.canvas.coords(self.token_halos[i], x - 14, y - 14, x + 14, y + 14)
            self.canvas.coords(self.tokens[i], x - 12, y - 12, x + 12, y + 12)
            self.canvas.coords(f"highlight{i}", x - 9, y - 9, x + 9, y + 9)
            self.canvas.coords(self.token_labels[i], x, y - 30)

    # ----- gameplay logic -----
    def roll_dice(self):
        """Start dice roll animation (non-blocking)"""
        if self.game_over or self.moving or self.dice_rolling:
            return

        # Multiplayer: ensure it's our allowed turn based on role
        if self.mode == "multiplayer":
            if (self.is_host and self.current_player != 0) or (not self.is_host and self.current_player != 1):
                self.status_label.config(text="Wait for your turn!")
                return

        self.dice_rolling = True
        self.roll_button.config(state=tk.DISABLED)
        self._animate_dice_roll()

    def _animate_dice_roll(self, frame=0):
        """Animate the dice rolling"""
        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        if frame < 10:
            self.dice_label.config(text=random.choice(dice_faces))
            self.window.after(80, lambda: self._animate_dice_roll(frame + 1))
        else:
            self.dice_value = random.randint(1, 6)
            self.dice_label.config(text=dice_faces[self.dice_value - 1])
            self.dice_rolling = False
            self.status_label.config(text=f"{self.player_names[self.current_player]} rolled {self.dice_value}!")

            # send dice_roll to network (multiplayer)
            if self.mode == "multiplayer" and self.websocket_connection:
                self.send_network_message(
                    {"type": "dice_roll", "player": self.current_player, "value": self.dice_value})

            # If solo and bot turn, auto-move
            if self.mode == "solo" and self.current_player == 1:
                self.window.after(700, lambda: self.try_move_token(1))

    def try_move_token(self, player_index):
        """Attempt to move a player's token after dice roll"""
        if (self.game_over or self.moving or self.dice_rolling or
                player_index != self.current_player or self.dice_value == 0):
            return

        # multiplayer guard: only local player may move
        if self.mode == "multiplayer":
            if (self.is_host and player_index != 0) or (not self.is_host and player_index != 1):
                return

        current_pos = self.positions[player_index]
        new_pos = current_pos + self.dice_value

        # overshoot -> pass turn
        if new_pos > 100:
            self.status_label.config(text="Overshot! Turn passes.")
            self.next_turn()
            return

        self.moving = True
        self.move_count[player_index] += 1
        self._animate_token_move(player_index, current_pos, new_pos)

    def _animate_token_move(self, player_index, start_pos, end_pos, step=0):
        """Animate token movement step by step"""
        total_steps = end_pos - start_pos
        if step < total_steps:
            self.positions[player_index] = start_pos + step + 1
            self.update_token_positions()
            self.window.after(140, lambda: self._animate_token_move(player_index, start_pos, end_pos, step + 1))
        else:
            final_pos = end_pos
            # after move, check for ladder or snake
            if final_pos in LADDERS:
                top = LADDERS[final_pos]
                self.status_label.config(text=f"{self.player_names[player_index]} climbed a ladder!")
                self.window.after(350, lambda: self.handle_special_move(player_index, top))
            elif final_pos in SNAKES:
                tail = SNAKES[final_pos]
                self.status_label.config(text=f"{self.player_names[player_index]} hit a snake!")
                self.window.after(350, lambda: self.handle_special_move(player_index, tail))
            else:
                self.complete_move(player_index, final_pos)

    def handle_special_move(self, player_index, new_pos):
        """Handle snake or ladder movement"""
        self.positions[player_index] = new_pos
        self.update_token_positions()
        self.complete_move(player_index, new_pos)

    def complete_move(self, player_index, final_pos):
        """Complete a player's move and check for win condition"""
        self.moving = False
        self.dice_value = 0

        # send move to opponent (multiplayer)
        if self.mode == "multiplayer" and self.websocket_connection:
            self.send_network_message({"type": "move", "player": player_index, "position": final_pos})

        # check win
        if final_pos >= 100:
            self.handle_game_end(player_index)
        else:
            self.next_turn()

    def next_turn(self):
        """Switch to the next player's turn"""
        self.current_player = 1 - self.current_player
        self.update_ui_state()
        if self.mode == "multiplayer" and self.websocket_connection:
            self.send_network_message({"type": "turn_change", "current_player": self.current_player})

    def handle_game_end(self, winner_index):
        """Handle game end and show results"""
        self.game_over = True
        winner_name = self.player_names[winner_index]
        game_duration = int(time.time() - self.start_time)
        self.status_label.config(text=f"🏆 {winner_name} WINS! 🏆")
        self.roll_button.config(state=tk.DISABLED)

        # save solo stats only
        if self.mode == "solo":
            self._save_local_stats(winner_index == 0, game_duration)

        result = messagebox.askquestion("Game Over",
                                        f"🏆 {winner_name} wins!\n"
                                        f"Game duration: {game_duration}s\n"
                                        f"Moves: P1={self.move_count[0]}, P2={self.move_count[1]}\n\n"
                                        "Play again?",
                                        icon='question')
        if result == "yes":
            self.reset_game()
        else:
            self.quit_game()

    def _save_local_stats(self, player_won, duration):
        """Save game statistics to local file"""
        try:
            stats_file = "game_stats.json"
            stats = {}
            if os.path.exists(stats_file):
                with open(stats_file, "r") as f:
                    stats = json.load(f)
            stats.setdefault("total_games", 0)
            stats.setdefault("wins", 0)
            stats.setdefault("losses", 0)
            stats.setdefault("best_time", None)

            stats["total_games"] += 1
            if player_won:
                stats["wins"] += 1
                if stats["best_time"] is None or duration < stats["best_time"]:
                    stats["best_time"] = duration
            else:
                stats["losses"] += 1

            with open(stats_file, "w") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            print("Error saving stats:", e)

    # ----- UI & state updates -----
    def update_ui_state(self):
        """Update UI to reflect current game state"""
        if self.game_over:
            return

        for i, label in enumerate(self.player_labels):
            if i == self.current_player:
                label.config(font=("Arial", 12, "bold"), relief=tk.RAISED)
            else:
                label.config(font=("Arial", 12, "normal"), relief=tk.FLAT)

        if self.mode == "multiplayer":
            # enable roll only for the local player's turn
            if (self.is_host and self.current_player == 0) or (not self.is_host and self.current_player == 1):
                self.status_label.config(text="Your turn - Roll the dice!")
                self.roll_button.config(state=tk.NORMAL)
            else:
                opponent_name = self.player_names[1 - self.current_player] if self.is_host else self.player_names[
                    self.current_player]
                self.status_label.config(text=f"Waiting for {opponent_name}...")
                self.roll_button.config(state=tk.DISABLED)
        else:
            self.status_label.config(text=f"{self.player_names[self.current_player]}'s turn")
            self.roll_button.config(state=tk.NORMAL)

    def reset_game(self):
        """Reset the game to initial state"""
        self.positions = [0, 0]
        self.dice_value = 0
        self.current_player = 0
        self.game_over = False
        self.moving = False
        self.dice_rolling = False
        self.move_count = [0, 0]
        self.start_time = time.time()
        self.dice_label.config(text="🎲")
        self.update_token_positions()
        self.update_ui_state()

        # notify opponent
        if self.mode == "multiplayer" and self.websocket_connection:
            self.send_network_message({"type": "reset"})

    def quit_game(self):
        """Quit the game and clean up"""
        if callable(self.on_game_end):
            try:
                # send end notification to client-side on_game_end with winner None
                self.on_game_end(None)
            except Exception:
                pass
        try:
            self.window.destroy()
        except Exception:
            pass

    # ----- Networking helpers (hooks) -----
    def send_network_message(self, data):
        """Send a game-level message through provided websocket_connection helper."""
        if self.websocket_connection:
            try:
                return self.websocket_connection.send_message(data)
            except Exception as e:
                print("Network send error:", e)
                return False
        return False

    def handle_network_message(self, data):
        """Handle an incoming message dict coming from GameClient (GameClient will call this)."""
        try:
            msg_type = data.get("type")
            if msg_type == "dice_roll":
                player = data.get("player")
                value = data.get("value")
                # only process opponent dice (not local)
                if player != (0 if self.is_host else 1):
                    self.dice_value = value
                    faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
                    self.dice_label.config(text=faces[value - 1])
                    self.status_label.config(text=f"{self.player_names[player]} rolled {value}!")
            elif msg_type == "move":
                player = data.get("player")
                position = data.get("position")
                # update opponent's position
                if player != (0 if self.is_host else 1):
                    self.positions[player] = position
                    self.update_token_positions()
            elif msg_type == "turn_change":
                self.current_player = data.get("current_player", self.current_player)
                self.update_ui_state()
            elif msg_type == "reset":
                self.reset_game()
            elif msg_type == "disconnect":
                self.handle_disconnect()
        except Exception as e:
            print("Network message handling error:", e)

    def handle_disconnect(self):
        """Handle opponent disconnection"""
        self.status_label.config(text="Opponent disconnected!")
        self.roll_button.config(state=tk.DISABLED)
        messagebox.showinfo("Disconnected", "The other player has disconnected.")

    def check_network_messages(self):
        """
        Periodic hook — currently used only to keep the after loop alive for future
        queued network tasks. Actual incoming messages should be routed from GameClient
        to handle_network_message(data).
        """
        if not self.game_over:
            # schedule again
            self.window.after(200, self.check_network_messages)


# ----- standalone run for testing -----
if __name__ == "__main__":
    root = tk.Tk()
    game = SnakeLadderGame(
        root,
        player_names=["Player", "Bot"],
        player_avatars=["🙂", "🤖"],
        mode="solo"
    )
    root.mainloop()