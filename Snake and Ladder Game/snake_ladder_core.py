import tkinter as tk
from tkinter import messagebox
import random
import json
import time
import os
import math
import asyncio
import threading

BOARD_SIZE = 640
TILE_SIZE = BOARD_SIZE // 10
BOARD_MARGIN = 40

SNAKES = {98: 78, 95: 56, 87: 24, 62: 18, 54: 34, 16: 6}
LADDERS = {1: 38, 4: 14, 9: 21, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100}


class SnakeLadderGame:

    def __init__(self, window, player_names, player_avatars, mode="solo",
                 websocket_connection=None, is_host=True, my_player_index=0, on_game_end=None):

        self.window = window
        self.window.title("Slide to Glory Game")
        self.window.configure(bg="#2c3e50")

        self.player_names = player_names or ["Player 1", "Player 2"]
        self.player_avatars = player_avatars or ["🙂", "😎"]
        self.mode = mode
        self.websocket_connection = websocket_connection
        self.is_host = is_host
        self.my_player_index = my_player_index
        self.on_game_end = on_game_end

        self.positions = [0, 0]
        self.dice_value = 0
        self.current_player = 0
        self.game_over = False

        self.my_turn = (self.current_player == self.my_player_index)

        self.moving = False
        self.dice_rolling = False

        self.start_time = time.time()
        self.move_count = [0, 0]

        self.message_queue = []
        self.queue_lock = threading.Lock()

        print(f"Game initialized - Mode: {mode}, My player: {my_player_index}, Is host: {is_host}")
        print(f"Player names: {self.player_names}")
        print(f"My turn: {self.my_turn}")

        self.setup_ui()
        self.create_board()
        self.create_tokens()
        self.update_ui_state()

        if mode == "multiplayer":
            self.process_network_messages()

        if self.mode == "solo" and self.current_player == 1:
            self.window.after(1000, self.bot_turn)

    def setup_ui(self):
        self.window.geometry("1000x750")
        self.window.resizable(True, True)  # Make window resizable
        self.window.minsize(800, 600)  # Set minimum size to ensure usability

        # Add fullscreen toggle functionality
        self.is_fullscreen = False
        self.window.bind('<F11>', self.toggle_fullscreen)
        self.window.bind('<Escape>', lambda e: self.exit_fullscreen())

        # Bind window resize event to adjust layout
        self.window.bind('<Configure>', self.on_window_resize)

        self.main_frame = tk.Frame(self.window, bg="#2c3e50")
        self.main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Create board container with centering capability
        self.board_container = tk.Frame(self.main_frame, bg="#34495e", relief=tk.RAISED, bd=3)

        canvas_size = BOARD_SIZE + BOARD_MARGIN * 2
        self.canvas = tk.Canvas(
            self.board_container,
            width=canvas_size,
            height=canvas_size,
            bg="#ecf0f1",
            highlightbackground="#34495e"
        )
        self.canvas.pack(padx=5, pady=5)

        # Create controls frame
        self.controls_frame = tk.Frame(self.main_frame, bg="#34495e", width=300, relief=tk.RAISED, bd=3)
        self.controls_frame.pack_propagate(False)

        # Initial layout
        self.update_layout()

        self.setup_controls(self.controls_frame)

    def setup_controls(self, parent):

        tk.Label(parent, text="Slide to Glory", font=("Arial", 18, "bold"),
                 bg="#34495e", fg="white").pack(pady=15)

        players_frame = tk.Frame(parent, bg="#2c3e50", relief=tk.SUNKEN, bd=2)
        players_frame.pack(pady=10, padx=15, fill="x")

        self.player_labels = []
        colors = ["#e74c3c", "#3498db"]

        for i in range(2):
            player_text = f"{self.player_avatars[i]} {self.player_names[i]}"
            if self.mode == "multiplayer" and i == self.my_player_index:
                player_text += " (You)"

            label = tk.Label(
                players_frame,
                text=player_text,
                font=("Arial", 12, "bold"),
                bg="#2c3e50",
                fg=colors[i]
            )
            label.pack(pady=3)
            self.player_labels.append(label)

        mode_text = f"Mode: {self.mode.title()}"
        if self.mode == "multiplayer":
            role = "Host" if self.is_host else "Guest"
            mode_text += f" ({role})"

        tk.Label(parent, text=mode_text, font=("Arial", 10),
                 bg="#34495e", fg="#bdc3c7").pack(pady=5)

        dice_frame = tk.Frame(parent, bg="#34495e")
        dice_frame.pack(pady=20)

        self.dice_label = tk.Label(
            dice_frame,
            text="🎲",
            font=("Arial", 50),
            bg="#34495e",
            fg="white"
        )
        self.dice_label.pack(pady=10)

        self.roll_button = tk.Button(
            dice_frame,
            text="Roll Dice",
            command=self.roll_dice,
            font=("Arial", 14, "bold"),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=10,
            width=12
        )
        self.roll_button.pack(pady=5)

        self.status_label = tk.Label(
            parent,
            text="Game starting...",
            font=("Arial", 12, "bold"),
            bg="#34495e",
            fg="#f1c40f",
            wraplength=260,
            justify="center"
        )
        self.status_label.pack(pady=15)

        controls_container = tk.Frame(parent, bg="#34495e")
        controls_container.pack(pady=10)

        tk.Button(
            controls_container,
            text="Toggle Fullscreen",
            command=self.toggle_fullscreen,
            font=("Arial", 12),
            bg="#9b59b6",
            fg="white",
            padx=15,
            pady=5,
            width=12
        ).pack(pady=3)

        tk.Button(
            controls_container,
            text="Reset Game",
            command=self.reset_game,
            font=("Arial", 12),
            bg="#e67e22",
            fg="white",
            padx=15,
            pady=5,
            width=12
        ).pack(pady=3)

        tk.Button(
            controls_container,
            text="Quit Game",
            command=self.quit_game,
            font=("Arial", 12),
            bg="#c0392b",
            fg="white",
            padx=15,
            pady=5,
            width=12
        ).pack(pady=3)

    def update_layout(self):

        self.board_container.pack_forget()
        self.controls_frame.pack_forget()

        window_width = self.window.winfo_width()

        if self.is_fullscreen or window_width > 1200:
            self.board_container.pack(side=tk.LEFT, expand=True, padx=5)
            self.controls_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        else:
            self.board_container.pack(side=tk.LEFT, padx=5)
            self.controls_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

    def on_window_resize(self, event):

        if event.widget == self.window:
            self.window.after_idle(self.update_layout)

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.window.attributes('-fullscreen', self.is_fullscreen)

        self.window.after(100, self.update_layout)

        if self.is_fullscreen:
            current_text = self.status_label.cget('text')
            if "Press F11 or Escape" not in current_text:
                self.window.after(2000, lambda: self.show_fullscreen_help())

        return "break"

    def show_fullscreen_help(self):
        if self.is_fullscreen and not self.game_over:
            current_text = self.status_label.cget('text')
            self.status_label.config(text=current_text + " | Press F11 or Escape to exit fullscreen")
            self.window.after(3000, self.restore_status_text)

    def restore_status_text(self):
        if hasattr(self, '_original_status'):
            self.status_label.config(text=self._original_status)
        else:
            current_text = self.status_label.cget('text')
            if " | Press F11 or Escape" in current_text:
                self.status_label.config(text=current_text.split(" | Press F11")[0])

    def exit_fullscreen(self):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.window.attributes('-fullscreen', False)
            self.window.after(100, self.update_layout)

    def create_board(self):

        colors = ["#3498db", "#85c1e9", "#aed6f1", "#d6eaf8"]

        for row in range(10):
            for col in range(10):
                x1 = col * TILE_SIZE + BOARD_MARGIN
                y1 = (9 - row) * TILE_SIZE + BOARD_MARGIN
                x2 = x1 + TILE_SIZE
                y2 = y1 + TILE_SIZE

                if row % 2 == 0:
                    square_num = row * 10 + col + 1
                else:
                    square_num = row * 10 + (9 - col) + 1

                color = colors[(row + col) % len(colors)]
                if square_num == 1:
                    color = "#27ae60"
                elif square_num == 100:
                    color = "#f1c40f"
                elif square_num in SNAKES:
                    color = "#e74c3c"
                elif square_num in LADDERS:
                    color = "#2ecc71"

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline="#2c3e50",
                    width=2
                )

                self.canvas.create_text(
                    x1 + TILE_SIZE // 2,
                    y1 + TILE_SIZE // 2,
                    text=str(square_num),
                    font=("Arial", 10, "bold"),
                    fill="#2c3e50"
                )

        self.draw_snakes_and_ladders()

    def draw_snakes_and_ladders(self):

        for head, tail in SNAKES.items():
            self.draw_cartoon_snake(head, tail)

        for bottom, top in LADDERS.items():
            self.draw_golden_ladder(bottom, top)

    def draw_cartoon_snake(self, head, tail):
        head_x, head_y = self.get_square_center(head)
        tail_x, tail_y = self.get_square_center(tail)

        distance = ((head_x - tail_x) ** 2 + (head_y - tail_y) ** 2) ** 0.5
        curve_intensity = min(distance * 0.3, 40)

        control1_x = head_x + (tail_x - head_x) * 0.25 + curve_intensity * math.sin(head * 0.1)
        control1_y = head_y + (tail_y - head_y) * 0.25 + curve_intensity * math.cos(head * 0.1)

        control2_x = head_x + (tail_x - head_x) * 0.75 - curve_intensity * math.sin(head * 0.1)
        control2_y = head_y + (tail_y - head_y) * 0.75 - curve_intensity * math.cos(head * 0.1)

        segments = 20
        snake_colors = ["#FF6B6B", "#FF8E53", "#FF6B9D", "#4ECDC4", "#45B7D1"]

        points = []
        for i in range(segments + 1):
            t = i / segments

            x = ((1 - t) ** 3 * head_x + 3 * (1 - t) ** 2 * t * control1_x +
                 3 * (1 - t) * t ** 2 * control2_x + t ** 3 * tail_x)
            y = ((1 - t) ** 3 * head_y + 3 * (1 - t) ** 2 * t * control1_y +
                 3 * (1 - t) * t ** 2 * control2_y + t ** 3 * tail_y)
            points.extend([x, y])

        self.canvas.create_line(
            points, fill="#2C3E50", width=16,
            smooth=True, capstyle=tk.ROUND, joinstyle=tk.ROUND
        )

        for i in range(len(snake_colors)):
            color = snake_colors[i]
            width = 14 - i * 2
            self.canvas.create_line(
                points, fill=color, width=width,
                smooth=True, capstyle=tk.ROUND, joinstyle=tk.ROUND
            )

        for i in range(0, len(points), 8):
            if i + 1 < len(points):
                pattern_x, pattern_y = points[i], points[i + 1]

                diamond_size = 4
                diamond_points = [
                    pattern_x, pattern_y - diamond_size,
                               pattern_x + diamond_size, pattern_y,
                    pattern_x, pattern_y + diamond_size,
                               pattern_x - diamond_size, pattern_y
                ]
                self.canvas.create_polygon(
                    diamond_points, fill="#FFD93D", outline="#F39C12", width=1
                )

        head_size = 18

        self.canvas.create_oval(
            head_x - head_size + 2, head_y - head_size + 2,
            head_x + head_size + 2, head_y + head_size + 2,
            fill="#2C3E50", outline=""
        )

        self.canvas.create_oval(
            head_x - head_size, head_y - head_size,
            head_x + head_size, head_y + head_size,
            fill="#FF6B6B", outline="#E74C3C", width=3
        )

        self.canvas.create_oval(
            head_x - head_size + 4, head_y - head_size + 4,
            head_x + head_size - 4, head_y + head_size - 4,
            fill="#FF8E8E", outline=""
        )

        eye_size = 6
        eye_offset = 8

        self.canvas.create_oval(
            head_x - eye_offset - eye_size, head_y - 4 - eye_size,
            head_x - eye_offset + eye_size, head_y - 4 + eye_size,
            fill="white", outline="#2C3E50", width=2
        )

        self.canvas.create_oval(
            head_x - eye_offset - 3, head_y - 4 - 3,
            head_x - eye_offset + 3, head_y - 4 + 3,
            fill="#2C3E50", outline=""
        )

        self.canvas.create_oval(
            head_x - eye_offset - 1, head_y - 4 - 2,
            head_x - eye_offset + 1, head_y - 4,
            fill="white", outline=""
        )

        self.canvas.create_oval(
            head_x + eye_offset - eye_size, head_y - 4 - eye_size,
            head_x + eye_offset + eye_size, head_y - 4 + eye_size,
            fill="white", outline="#2C3E50", width=2
        )

        self.canvas.create_oval(
            head_x + eye_offset - 3, head_y - 4 - 3,
            head_x + eye_offset + 3, head_y - 4 + 3,
            fill="#2C3E50", outline=""
        )

        self.canvas.create_oval(
            head_x + eye_offset - 1, head_y - 4 - 2,
            head_x + eye_offset + 1, head_y - 4,
            fill="white", outline=""
        )

        smile_points = [
            head_x - 8, head_y + 4,
            head_x - 4, head_y + 8,
            head_x, head_y + 6,
            head_x + 4, head_y + 8,
            head_x + 8, head_y + 4
        ]
        self.canvas.create_line(
            smile_points, fill="#2C3E50", width=3,
            smooth=True, capstyle=tk.ROUND
        )

    def draw_golden_ladder(self, bottom, top):

        bottom_x, bottom_y = self.get_square_center(bottom)
        top_x, top_y = self.get_square_center(top)

        side_width = 10
        glow_offset = 2

        glow_colors = ["#FFD700", "#FFA500", "#FF8C00"]
        for i, glow_color in enumerate(glow_colors):
            width = 12 - i * 2

            self.canvas.create_line(
                bottom_x - side_width, bottom_y,
                top_x - side_width, top_y,
                fill=glow_color, width=width,
                capstyle=tk.ROUND
            )

            self.canvas.create_line(
                bottom_x + side_width, bottom_y,
                top_x + side_width, top_y,
                fill=glow_color, width=width,
                capstyle=tk.ROUND
            )

        self.canvas.create_line(
            bottom_x - side_width, bottom_y,
            top_x - side_width, top_y,
            fill="#B8860B", width=8,
            capstyle=tk.ROUND
        )

        self.canvas.create_line(
            bottom_x - side_width - 2, bottom_y,
            top_x - side_width - 2, top_y,
            fill="#FFD700", width=4,
            capstyle=tk.ROUND
        )

        self.canvas.create_line(
            bottom_x + side_width, bottom_y,
            top_x + side_width, top_y,
            fill="#B8860B", width=8,
            capstyle=tk.ROUND
        )

        self.canvas.create_line(
            bottom_x + side_width + 2, bottom_y,
            top_x + side_width + 2, top_y,
            fill="#FFD700", width=4,
            capstyle=tk.ROUND
        )

        ladder_height = ((top_x - bottom_x) ** 2 + (top_y - bottom_y) ** 2) ** 0.5
        rungs = max(3, min(10, int(ladder_height / 25)))

        for i in range(rungs):
            t = (i + 1) / (rungs + 1)
            rung_x1 = bottom_x + (top_x - bottom_x) * t - side_width
            rung_y1 = bottom_y + (top_y - bottom_y) * t
            rung_x2 = bottom_x + (top_x - bottom_x) * t + side_width
            rung_y2 = bottom_y + (top_y - bottom_y) * t

            self.canvas.create_line(
                rung_x1 - 2, rung_y1, rung_x2 + 2, rung_y2,
                fill="#FFD700", width=8, capstyle=tk.ROUND
            )

            self.canvas.create_line(
                rung_x1, rung_y1, rung_x2, rung_y2,
                fill="#B8860B", width=6, capstyle=tk.ROUND
            )

            self.canvas.create_line(
                rung_x1, rung_y1 - 1, rung_x2, rung_y2 - 1,
                fill="#FFFF00", width=3, capstyle=tk.ROUND
            )

            sparkle_positions = [0.25, 0.5, 0.75]
            for sparkle_pos in sparkle_positions:
                sparkle_x = rung_x1 + (rung_x2 - rung_x1) * sparkle_pos
                sparkle_y = rung_y1 + (rung_y2 - rung_y1) * sparkle_pos

                star_size = 3
                star_points = []
                for angle in range(0, 360, 45):  # 8-pointed star
                    radius = star_size if angle % 90 == 0 else star_size * 0.5
                    x = sparkle_x + radius * math.cos(math.radians(angle))
                    y = sparkle_y + radius * math.sin(math.radians(angle))
                    star_points.extend([x, y])

                self.canvas.create_polygon(
                    star_points, fill="#FFFFFF", outline="#FFD700", width=1
                )

        sparkle_count = int(ladder_height / 30)
        for _ in range(sparkle_count):
            t = random.random()
            spark_x = bottom_x + (top_x - bottom_x) * t + random.randint(-15, 15)
            spark_y = bottom_y + (top_y - bottom_y) * t + random.randint(-10, 10)

            spark_size = random.randint(2, 4)
            self.canvas.create_oval(
                spark_x - spark_size, spark_y - spark_size,
                spark_x + spark_size, spark_y + spark_size,
                fill="#FFFF00", outline="#FFD700", width=1
            )

            cross_size = spark_size + 2
            self.canvas.create_line(
                spark_x - cross_size, spark_y, spark_x + cross_size, spark_y,
                fill="#FFFFFF", width=1
            )
            self.canvas.create_line(
                spark_x, spark_y - cross_size, spark_x, spark_y + cross_size,
                fill="#FFFFFF", width=1
            )

    def get_square_center(self, square_num):
        if square_num <= 0:
            return BOARD_MARGIN // 2, BOARD_SIZE + BOARD_MARGIN + BOARD_MARGIN // 2

        if square_num > 100:
            square_num = 100

        square_num -= 1
        row = square_num // 10

        if row % 2 == 0:
            col = square_num % 10
        else:
            col = 9 - (square_num % 10)

        x = col * TILE_SIZE + TILE_SIZE // 2 + BOARD_MARGIN
        y = BOARD_SIZE - (row * TILE_SIZE + TILE_SIZE // 2) + BOARD_MARGIN

        return x, y

    def update_token_positions(self):
        for i in range(2):
            if self.positions[i] <= 0:
                if i == 0:
                    x, y = BOARD_MARGIN // 2, BOARD_SIZE + BOARD_MARGIN + 15
                else:
                    x, y = BOARD_SIZE + BOARD_MARGIN + BOARD_MARGIN // 2, BOARD_SIZE + BOARD_MARGIN + 15
            else:
                x, y = self.get_square_center(self.positions[i])
                if i == 0:
                    x -= 10
                    y -= 10
                else:
                    x += 10
                    y += 10

            self.canvas.coords(self.tokens[i], x, y)

    def create_tokens(self):
        self.tokens = []
        colors = ["#c0392b", "#1e3a8a"]

        for i in range(2):
            token = self.canvas.create_text(
                0, 0,
                text=self.player_avatars[i],
                font=("Arial", 24, "bold"),
                fill=colors[i],
                tags=f"player{i}"
            )
            self.tokens.append(token)

            if self.mode == "solo":
                if i == 0:  # Only player 0 can click their token
                    self.canvas.tag_bind(f"player{i}", "<Button-1>",
                                         lambda e, p=i: self.try_move_token(p))
            elif self.mode == "multiplayer":
                if i == self.my_player_index:  # Only my token can be clicked
                    self.canvas.tag_bind(f"player{i}", "<Button-1>",
                                         lambda e, p=i: self.try_move_token(p))

        self.update_token_positions()

    def roll_dice(self):
        if self.game_over or self.moving or self.dice_rolling:
            print("Cannot roll dice - game state prevents it")
            return

        if self.mode == "multiplayer":
            if not self.my_turn:
                self.status_label.config(text="Wait for your turn!")
                print(f"Not my turn - current player: {self.current_player}, my index: {self.my_player_index}")
                return
        elif self.mode == "solo":
            if self.current_player != 0:
                print(f"Solo mode - not player 0's turn (current: {self.current_player})")
                return

        print(f"Rolling dice - Current player: {self.current_player}, My index: {self.my_player_index}")

        self.dice_rolling = True
        self.roll_button.config(state=tk.DISABLED)
        self.animate_dice_roll()

    def bot_turn(self):
        if self.game_over or self.moving or self.dice_rolling:
            return

        if self.mode != "solo" or self.current_player != 1:
            return

        print("Bot's turn starting...")
        self.status_label.config(text=f"{self.player_names[1]} (Bot) is thinking...")

        self.window.after(800, self.bot_roll_dice)

    def bot_roll_dice(self):
        if self.game_over or self.moving or self.dice_rolling:
            return

        if self.mode != "solo" or self.current_player != 1:
            return

        print("Bot rolling dice...")
        self.dice_rolling = True
        self.animate_dice_roll()

    def animate_dice_roll(self, frame=0, final_value=None):
        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

        if frame < 10:
            random_face = random.choice(dice_faces)
            self.dice_label.config(text=random_face)
            self.window.after(100, lambda: self.animate_dice_roll(frame + 1, final_value))
        else:
            if final_value is None:

                self.dice_value = random.randint(1, 6)
                final_value = self.dice_value

                if self.mode == "multiplayer" and self.websocket_connection:
                    success = self.send_network_message({
                        "type": "dice_roll",
                        "player": self.current_player,
                        "value": self.dice_value
                    })
                    print(f"Sent dice roll message: {success}")
            else:
                self.dice_value = final_value

            self.dice_label.config(text=dice_faces[final_value - 1])
            self.dice_rolling = False
            self.status_label.config(text=f"{self.player_names[self.current_player]} rolled {final_value}!")

            print(f"Dice animation complete: {final_value} by player {self.current_player}")

            if self.mode == "solo":
                if self.current_player == 1:
                    self.window.after(800, lambda: self.try_move_token(1))
                else:
                    self.status_label.config(text=f"Click your avatar to move {final_value} spaces!")
            elif self.mode == "multiplayer":
                if self.my_turn:
                    self.status_label.config(text=f"Click your avatar to move {final_value} spaces!")
                else:
                    self.status_label.config(text=f"Opponent is moving {final_value} spaces...")

    def try_move_token(self, player_index):
        if (self.game_over or self.moving or self.dice_rolling or
                self.dice_value == 0):
            print(f"Cannot move token - game state prevents it (dice: {self.dice_value})")
            return

        if player_index != self.current_player:
            print(f"Wrong player trying to move: {player_index}, current: {self.current_player}")
            return

        if self.mode == "multiplayer":
            if not self.my_turn:
                print(f"Not my turn: trying {player_index}, my index: {self.my_player_index}")
                return

        current_pos = self.positions[player_index]
        new_pos = current_pos + self.dice_value

        print(f"Moving player {player_index} from {current_pos} to {new_pos}")

        if new_pos > 100:
            self.status_label.config(text=f"{self.player_names[player_index]} overshot! Turn passes.")
            self.window.after(1000, self.next_turn)
            return

        self.moving = True
        self.move_count[player_index] += 1
        self.animate_token_move(player_index, current_pos, new_pos)

    def animate_token_move(self, player_index, start_pos, end_pos, step=0, is_opponent_move=False):
        total_steps = end_pos - start_pos

        if step < total_steps:
            self.positions[player_index] = start_pos + step + 1
            self.update_token_positions()
            self.window.after(150, lambda: self.animate_token_move(player_index, start_pos, end_pos, step + 1,
                                                                   is_opponent_move))
        else:
            final_pos = end_pos

            if final_pos in LADDERS:
                ladder_top = LADDERS[final_pos]
                self.status_label.config(text=f"{self.player_names[player_index]} climbed a ladder!")
                self.window.after(500, lambda: self.handle_special_move(player_index, ladder_top, is_opponent_move))
            elif final_pos in SNAKES:
                snake_tail = SNAKES[final_pos]
                self.status_label.config(text=f"{self.player_names[player_index]} hit a snake!")
                self.window.after(500, lambda: self.handle_special_move(player_index, snake_tail, is_opponent_move))
            else:
                self.complete_move(player_index, final_pos, is_opponent_move)

    def handle_special_move(self, player_index, new_pos, is_opponent_move=False):
        self.positions[player_index] = new_pos
        self.update_token_positions()
        self.complete_move(player_index, new_pos, is_opponent_move)

    def complete_move(self, player_index, final_pos, is_opponent_move=False):
        self.moving = False
        self.dice_value = 0

        print(f"Move completed - Player {player_index} at position {final_pos}")

        if self.mode == "multiplayer" and self.websocket_connection and not is_opponent_move:
            success = self.send_network_message({
                "type": "move_complete",
                "player": player_index,
                "position": final_pos,
                "move_count": self.move_count[player_index]
            })
            print(f"Sent move complete message: {success}")

        if final_pos >= 100:
            self.handle_game_end(player_index)
        else:
            if not is_opponent_move:
                self.next_turn()
            else:
                self.update_ui_state()

    def next_turn(self):
        self.current_player = 1 - self.current_player
        self.dice_value = 0

        if self.mode == "multiplayer":
            self.my_turn = (self.current_player == self.my_player_index)

        print(f"Turn changed to player {self.current_player} (My turn: {getattr(self, 'my_turn', 'N/A')})")

        self.update_ui_state()

        if self.mode == "multiplayer" and self.websocket_connection:
            success = self.send_network_message({
                "type": "turn_change",
                "current_player": self.current_player
            })
            print(f"Sent turn change message: {success}")

        if self.mode == "solo" and self.current_player == 1:
            self.window.after(1000, self.bot_turn)

    def handle_game_end(self, winner_index):
        self.game_over = True
        winner_name = self.player_names[winner_index]
        game_duration = int(time.time() - self.start_time)

        self.status_label.config(text=f"🏆 {winner_name} WINS! 🏆")
        self.roll_button.config(state=tk.DISABLED)

        print(f"Game ended - Winner: {winner_name} (Player {winner_index})")

        if self.mode == "multiplayer" and self.websocket_connection:
            success = self.send_network_message({
                "type": "game_end",
                "winner": winner_index
            })
            print(f"Sent game end message: {success}")

        # ✅ Notify parent so stats update
        if callable(self.on_game_end):
            self.on_game_end(winner_index, game_duration)

        self.show_game_over_dialog(winner_index, winner_name, game_duration)

    def show_game_over_dialog(self, winner_index, winner_name, game_duration):
        """Show a beautiful game over dialog with winner announcement and options"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Game Over")
        dialog.geometry("700x550")
        dialog.configure(bg="#2c3e50")
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (550 // 2)
        dialog.geometry(f"700x550+{x}+{y}")

        # Header with trophy
        header = tk.Frame(dialog, bg="#f39c12", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🏆 GAME OVER 🏆", font=("Arial", 24, "bold"),
                 bg="#f39c12", fg="white").pack(pady=20)

        # Main content
        content = tk.Frame(dialog, bg="#2c3e50", padx=30, pady=20)
        content.pack(expand=True, fill="both")

        # Winner announcement
        winner_frame = tk.Frame(content, bg="#27ae60", relief=tk.RAISED, bd=3)
        winner_frame.pack(pady=15, padx=20, fill="x")

        winner_avatar = self.player_avatars[winner_index] if winner_index < len(self.player_avatars) else "🎉"
        tk.Label(winner_frame, text=f"{winner_avatar} {winner_name} WINS! {winner_avatar}",
                 font=("Arial", 20, "bold"), bg="#27ae60", fg="white").pack(pady=15)

        # Check if this is the player who won in multiplayer
        is_my_win = False
        if self.mode == "multiplayer" and hasattr(self, 'my_player_index'):
            is_my_win = (winner_index == self.my_player_index)

        if is_my_win:
            tk.Label(winner_frame, text="Congratulations! You are the champion!",
                     font=("Arial", 12, "bold"), bg="#27ae60", fg="#f1c40f").pack(pady=5)
        elif self.mode == "multiplayer":
            tk.Label(winner_frame, text="Better luck next time!",
                     font=("Arial", 12), bg="#27ae60", fg="white").pack(pady=5)

        # Game statistics
        stats_frame = tk.Frame(content, bg="#34495e", relief=tk.RAISED, bd=2)
        stats_frame.pack(pady=15, padx=20, fill="x")

        tk.Label(stats_frame, text="📊 Game Statistics", font=("Arial", 14, "bold"),
                 bg="#34495e", fg="white").pack(pady=8)

        # Format game duration
        minutes = game_duration // 60
        seconds = game_duration % 60
        duration_text = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        stats_text = f"Duration: {duration_text}"
        tk.Label(stats_frame, text=stats_text, font=("Arial", 11),
                 bg="#34495e", fg="#bdc3c7").pack(pady=2)

        moves_text = f"Moves - {self.player_names[0]}: {self.move_count[0]} | {self.player_names[1]}: {self.move_count[1]}"
        tk.Label(stats_frame, text=moves_text, font=("Arial", 11),
                 bg="#34495e", fg="#bdc3c7").pack(pady=2)

        # Buttons
        button_frame = tk.Frame(content, bg="#2c3e50")
        button_frame.pack(pady=20)

        def play_again():
            dialog.destroy()
            self.reset_game()

        def return_to_menu():
            dialog.destroy()
            self.quit_game()

        # Play Again button
        tk.Button(button_frame, text="🎮 Play Again", command=play_again,
                  font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                  padx=25, pady=12, width=12).pack(side=tk.LEFT, padx=10)

        # Return to Menu button
        tk.Button(button_frame, text="🏠 Main Menu", command=return_to_menu,
                  font=("Arial", 14, "bold"), bg="#3498db", fg="white",
                  padx=25, pady=12, width=12).pack(side=tk.RIGHT, padx=10)

        # Add some encouraging messages based on game performance
        self.add_performance_message(content, winner_index, game_duration)

        # Focus on dialog
        dialog.focus_set()

        # Bind Escape key to close dialog
        dialog.bind('<Escape>', lambda e: return_to_menu())
        dialog.bind('<Return>', lambda e: play_again())

    def add_performance_message(self, parent, winner_index, game_duration):
        """Add encouraging messages based on game performance"""
        message_frame = tk.Frame(parent, bg="#2c3e50")
        message_frame.pack(pady=10)

        message = ""
        message_color = "#95a5a6"

        # Performance-based messages
        if game_duration < 60:
            message = "⚡ Lightning fast game!"
            message_color = "#f1c40f"
        elif game_duration < 180:
            message = "⏱️ Quick and exciting!"
            message_color = "#e67e22"
        elif game_duration < 300:
            message = "🎯 Well-played game!"
            message_color = "#3498db"
        else:
            message = "🏰 Epic battle!"
            message_color = "#9b59b6"

        # Move efficiency messages
        total_moves = sum(self.move_count)
        if total_moves < 20:
            message += " Very efficient!"
        elif total_moves < 40:
            message += " Good strategy!"
        else:
            message += " Intense competition!"

        if message:
            tk.Label(message_frame, text=message, font=("Arial", 12, "italic"),
                     bg="#2c3e50", fg=message_color).pack(pady=5)

    def update_ui_state(self):
        if self.game_over:
            return

        for i, label in enumerate(self.player_labels):
            if i == self.current_player:
                label.config(font=("Arial", 12, "bold"), relief=tk.RAISED)
            else:
                label.config(font=("Arial", 12, "normal"), relief=tk.FLAT)

        if self.mode == "multiplayer":
            if self.my_turn:
                self.status_label.config(text="Your turn - Roll the dice!")
                self.roll_button.config(state=tk.NORMAL)
            else:
                opponent_name = self.player_names[1 - self.my_player_index]
                self.status_label.config(text=f"Waiting for {opponent_name}...")
                self.roll_button.config(state=tk.DISABLED)
        else:
            if self.current_player == 0:
                self.status_label.config(text=f"{self.player_names[self.current_player]}'s turn - Roll the dice!")
                self.roll_button.config(state=tk.NORMAL)
            else:
                self.status_label.config(text=f"{self.player_names[self.current_player]}'s turn (Bot)")
                self.roll_button.config(state=tk.DISABLED)

    def reset_game(self):
        self.positions = [0, 0]
        self.dice_value = 0
        self.current_player = 0
        self.game_over = False
        self.moving = False
        self.dice_rolling = False
        self.move_count = [0, 0]
        self.start_time = time.time()

        if self.mode == "multiplayer":
            self.my_turn = (self.current_player == self.my_player_index)

        self.dice_label.config(text="🎲")
        self.update_token_positions()
        self.update_ui_state()

        print("Game reset")

        if self.mode == "multiplayer" and self.websocket_connection:
            self.send_network_message({"type": "reset"})

        if self.mode == "solo" and self.current_player == 1:
            self.window.after(1000, self.bot_turn)

    def quit_game(self):
        if callable(self.on_game_end):
            self.on_game_end(None)
        self.window.destroy()

    def send_network_message(self, data):
        if self.websocket_connection:
            return self.websocket_connection.send_message(data)
        return False

    def handle_network_message(self, data):
        with self.queue_lock:
            self.message_queue.append(data)

    def process_network_messages(self):
        try:
            with self.queue_lock:
                messages_to_process = self.message_queue.copy()
                self.message_queue.clear()

            for data in messages_to_process:
                self._process_single_message(data)

        except Exception as e:
            print(f"Error processing network messages: {e}")

        if not self.game_over:
            self.window.after(100, self.process_network_messages)

    def _process_single_message(self, data):
        try:
            msg_type = data.get("type")
            print(f"Processing network message: {data}")

            if msg_type == "dice_roll":
                player = data.get("player")
                value = data.get("value")
                if player != self.my_player_index:
                    print(f"Showing opponent's dice roll: {value}")
                    self.dice_rolling = True
                    self.roll_button.config(state=tk.DISABLED)
                    self.animate_dice_roll(final_value=value)

            elif msg_type == "move_complete":
                player = data.get("player")
                position = data.get("position")
                move_count = data.get("move_count", 0)

                if player != self.my_player_index:
                    print(f"Processing opponent move from {self.positions[player]} to {position}")
                    old_pos = self.positions[player]
                    self.move_count[player] = move_count

                    if old_pos != position:
                        self.moving = True
                        self.animate_token_move(player, old_pos, position, is_opponent_move=True)
                    else:
                        self.positions[player] = position
                        self.update_token_positions()

            elif msg_type == "turn_change":
                new_current_player = data.get("current_player")
                if new_current_player != self.current_player:
                    self.current_player = new_current_player
                    self.my_turn = (self.current_player == self.my_player_index)
                    self.dice_value = 0
                    self.update_ui_state()
                    print(f"Turn changed via network to player {new_current_player} (My turn: {self.my_turn})")
                else:
                    print(f"Received redundant turn change message for player {new_current_player}")

            elif msg_type == "reset":
                self.reset_game()

            elif msg_type == "game_end":
                winner = data.get("winner")
                if not self.game_over:
                    self.handle_game_end(winner)

        except Exception as e:
            print(f"Error processing single network message: {e}")

    def handle_disconnect(self):
        self.status_label.config(text="Opponent disconnected!")
        self.roll_button.config(state=tk.DISABLED)
        messagebox.showinfo("Disconnected", "The other player has disconnected.")


if __name__ == "__main__":
    root = tk.Tk()
    game = SnakeLadderGame(
        root,
        player_names=["Player", "Bot"],
        player_avatars=["🙂", "🤖"],
        mode="solo"
    )
    root.mainloop()