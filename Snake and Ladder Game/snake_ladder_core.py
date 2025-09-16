#!/usr/bin/env python3
"""
Clean Snake & Ladder Game Core Logic
Handles game rules, UI, and network synchronization
"""

import tkinter as tk
from tkinter import messagebox
import random
import json
import time
import os
import math

# Game constants
BOARD_SIZE = 640
TILE_SIZE = BOARD_SIZE // 10
BOARD_MARGIN = 40

# Snakes and ladders positions
SNAKES = {98: 78, 95: 56, 87: 24, 62: 18, 54: 34, 16: 6}
LADDERS = {1: 38, 4: 14, 9: 21, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100}


class SnakeLadderGame:
    """Main game class for Snake & Ladder"""

    def __init__(self, window, player_names, player_avatars, mode="solo",
                 websocket_connection=None, is_host=True, on_game_end=None):

        self.window = window
        self.window.title("Snake & Ladder Game")
        self.window.configure(bg="#2c3e50")

        # Game parameters
        self.player_names = player_names or ["Player 1", "Player 2"]
        self.player_avatars = player_avatars or ["🙂", "😎"]
        self.mode = mode  # "solo", "multiplayer"
        self.websocket_connection = websocket_connection
        self.is_host = is_host
        self.on_game_end = on_game_end

        # Game state
        self.positions = [0, 0]
        self.dice_value = 0
        self.current_player = 0
        self.game_over = False
        self.my_turn = self.is_host if mode == "multiplayer" else True

        # Animation state
        self.moving = False
        self.dice_rolling = False

        # Statistics
        self.start_time = time.time()
        self.move_count = [0, 0]

        # Initialize UI
        self.setup_ui()
        self.create_board()
        self.create_tokens()
        self.update_ui_state()

        # Network message processing for multiplayer
        if mode == "multiplayer":
            self.check_network_messages()

    def setup_ui(self):
        """Setup game UI components"""
        # Set window size and position
        self.window.geometry("1000x750")
        self.window.resizable(False, False)

        # Main container
        main_frame = tk.Frame(self.window, bg="#2c3e50")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Board container (left side)
        board_container = tk.Frame(main_frame, bg="#34495e", relief=tk.RAISED, bd=3)
        board_container.pack(side=tk.LEFT, padx=5)

        # Canvas for game board
        canvas_size = BOARD_SIZE + BOARD_MARGIN * 2
        self.canvas = tk.Canvas(
            board_container,
            width=canvas_size,
            height=canvas_size,
            bg="#ecf0f1",
            highlightbackground="#34495e"
        )
        self.canvas.pack(padx=5, pady=5)

        # Controls container (right side)
        controls_frame = tk.Frame(main_frame, bg="#34495e", width=300, relief=tk.RAISED, bd=3)
        controls_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        controls_frame.pack_propagate(False)

        self.setup_controls(controls_frame)

    def setup_controls(self, parent):
        """Setup game controls UI"""
        # Title
        tk.Label(parent, text="Snake & Ladder", font=("Arial", 18, "bold"),
                 bg="#34495e", fg="white").pack(pady=15)

        # Players display
        players_frame = tk.Frame(parent, bg="#2c3e50", relief=tk.SUNKEN, bd=2)
        players_frame.pack(pady=10, padx=15, fill="x")

        self.player_labels = []
        colors = ["#e74c3c", "#3498db"]

        for i in range(2):
            label = tk.Label(
                players_frame,
                text=f"{self.player_avatars[i]} {self.player_names[i]}",
                font=("Arial", 12, "bold"),
                bg="#2c3e50",
                fg=colors[i]
            )
            label.pack(pady=3)
            self.player_labels.append(label)

        # Game mode display
        mode_text = f"Mode: {self.mode.title()}"
        if self.mode == "multiplayer":
            role = "Host" if self.is_host else "Guest"
            mode_text += f" ({role})"

        tk.Label(parent, text=mode_text, font=("Arial", 10),
                 bg="#34495e", fg="#bdc3c7").pack(pady=5)

        # Dice display
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

        # Roll dice button
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

        # Status display
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

        # Game controls
        controls_container = tk.Frame(parent, bg="#34495e")
        controls_container.pack(pady=10)

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

    def create_board(self):
        """Create the game board"""
        # Board colors
        colors = ["#3498db", "#85c1e9", "#aed6f1", "#d6eaf8"]

        # Draw squares
        for row in range(10):
            for col in range(10):
                x1 = col * TILE_SIZE + BOARD_MARGIN
                y1 = (9 - row) * TILE_SIZE + BOARD_MARGIN
                x2 = x1 + TILE_SIZE
                y2 = y1 + TILE_SIZE

                # Calculate square number
                if row % 2 == 0:
                    square_num = row * 10 + col + 1
                else:
                    square_num = row * 10 + (9 - col) + 1

                # Choose color based on square type
                color = colors[(row + col) % len(colors)]
                if square_num == 1:
                    color = "#27ae60"  # Start - green
                elif square_num == 100:
                    color = "#f1c40f"  # End - yellow
                elif square_num in SNAKES:
                    color = "#e74c3c"  # Snake head - red
                elif square_num in LADDERS:
                    color = "#2ecc71"  # Ladder bottom - green

                # Draw square
                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline="#2c3e50",
                    width=2
                )

                # Add square number
                self.canvas.create_text(
                    x1 + TILE_SIZE // 2,
                    y1 + TILE_SIZE // 2,
                    text=str(square_num),
                    font=("Arial", 10, "bold"),
                    fill="#2c3e50"
                )

        # Draw snakes and ladders
        self.draw_snakes_and_ladders()

    def draw_snakes_and_ladders(self):
        """Draw snakes and ladders on the board"""
        # Draw snakes
        for head, tail in SNAKES.items():
            head_x, head_y = self.get_square_center(head)
            tail_x, tail_y = self.get_square_center(tail)

            # Draw snake body
            self.canvas.create_line(
                head_x, head_y, tail_x, tail_y,
                fill="#c0392b",
                width=6,
                smooth=True,
                capstyle=tk.ROUND,
                arrow=tk.LAST,
                arrowshape=(12, 15, 5)
            )

            # Snake head
            self.canvas.create_oval(
                head_x - 8, head_y - 8,
                head_x + 8, head_y + 8,
                fill="#e74c3c",
                outline="#c0392b",
                width=2
            )

        # Draw ladders
        for bottom, top in LADDERS.items():
            bottom_x, bottom_y = self.get_square_center(bottom)
            top_x, top_y = self.get_square_center(top)

            # Ladder sides
            offset = 6
            self.canvas.create_line(
                bottom_x - offset, bottom_y,
                top_x - offset, top_y,
                fill="#27ae60",
                width=4
            )
            self.canvas.create_line(
                bottom_x + offset, bottom_y,
                top_x + offset, top_y,
                fill="#27ae60",
                width=4
            )

            # Ladder rungs
            steps = 5
            for i in range(1, steps):
                step_y = bottom_y + (top_y - bottom_y) * i / steps
                step_x1 = bottom_x + (top_x - bottom_x) * i / steps - offset
                step_x2 = bottom_x + (top_x - bottom_x) * i / steps + offset

                self.canvas.create_line(
                    step_x1, step_y, step_x2, step_y,
                    fill="#2ecc71",
                    width=3
                )

    def create_tokens(self):
        """Create player tokens"""
        self.tokens = []
        self.token_labels = []
        colors = ["#e74c3c", "#3498db"]

        for i in range(2):
            # Token circle
            token = self.canvas.create_oval(
                0, 0, 20, 20,
                fill=colors[i],
                outline="white",
                width=2,
                tags=f"player{i}"
            )
            self.tokens.append(token)

            # Token label (avatar)
            label = self.canvas.create_text(
                0, 0,
                text=self.player_avatars[i],
                font=("Arial", 14),
                fill="white",
                tags=f"label{i}"
            )
            self.token_labels.append(label)

            # Bind click events
            if self.mode == "solo":
                # In solo mode, allow clicking any token on appropriate turn
                self.canvas.tag_bind(f"player{i}", "<Button-1>",
                                     lambda e, p=i: self.try_move_token(p))
            elif self.mode == "multiplayer":
                # In multiplayer, only allow clicking own token
                if (self.is_host and i == 0) or (not self.is_host and i == 1):
                    self.canvas.tag_bind(f"player{i}", "<Button-1>",
                                         lambda e, p=i: self.try_move_token(p))

        # Position tokens at start
        self.update_token_positions()

    def get_square_center(self, square_num):
        """Get center coordinates of a square"""
        if square_num <= 0:
            return BOARD_MARGIN // 2, BOARD_SIZE + BOARD_MARGIN + BOARD_MARGIN // 2

        if square_num > 100:
            square_num = 100

        square_num -= 1  # Convert to 0-based
        row = square_num // 10

        if row % 2 == 0:
            col = square_num % 10
        else:
            col = 9 - (square_num % 10)

        x = col * TILE_SIZE + TILE_SIZE // 2 + BOARD_MARGIN
        y = BOARD_SIZE - (row * TILE_SIZE + TILE_SIZE // 2) + BOARD_MARGIN

        return x, y

    def update_token_positions(self):
        """Update visual position of tokens"""
        for i in range(2):
            if self.positions[i] <= 0:
                # Starting position
                if i == 0:
                    x, y = BOARD_MARGIN // 2, BOARD_SIZE + BOARD_MARGIN + 15
                else:
                    x, y = BOARD_SIZE + BOARD_MARGIN + BOARD_MARGIN // 2, BOARD_SIZE + BOARD_MARGIN + 15
            else:
                x, y = self.get_square_center(self.positions[i])
                # Offset tokens so they don't overlap
                if i == 0:
                    x -= 10
                    y -= 10
                else:
                    x += 10
                    y += 10

            # Update token position
            self.canvas.coords(self.tokens[i], x - 10, y - 10, x + 10, y + 10)
            # Update label position
            self.canvas.coords(self.token_labels[i], x, y - 25)

    def roll_dice(self):
        """Roll the dice"""
        if self.game_over or self.moving or self.dice_rolling:
            return

        # Check if it's player's turn
        if self.mode == "multiplayer":
            if (self.is_host and self.current_player != 0) or (not self.is_host and self.current_player != 1):
                self.status_label.config(text="Wait for your turn!")
                return
        elif self.mode == "solo":
            if self.current_player != 0 and self.current_player != 1:
                return

        self.dice_rolling = True
        self.roll_button.config(state=tk.DISABLED)
        self.animate_dice_roll()

    def animate_dice_roll(self, frame=0):
        """Animate dice rolling"""
        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

        if frame < 10:
            # Show random dice face during animation
            random_face = random.choice(dice_faces)
            self.dice_label.config(text=random_face)
            self.window.after(100, lambda: self.animate_dice_roll(frame + 1))
        else:
            # Final dice value
            self.dice_value = random.randint(1, 6)
            self.dice_label.config(text=dice_faces[self.dice_value - 1])

            self.dice_rolling = False
            self.status_label.config(text=f"{self.player_names[self.current_player]} rolled {self.dice_value}!")

            # Send dice roll to opponent in multiplayer
            if self.mode == "multiplayer" and self.websocket_connection:
                self.send_network_message({
                    "type": "dice_roll",
                    "player": self.current_player,
                    "value": self.dice_value
                })

            # Auto-move for bot in solo mode
            if self.mode == "solo" and self.current_player == 1:
                self.window.after(1000, lambda: self.try_move_token(1))

    def try_move_token(self, player_index):
        """Try to move a token"""
        if (self.game_over or self.moving or self.dice_rolling or
                player_index != self.current_player or self.dice_value == 0):
            return

        # In multiplayer, check if it's the correct player's turn
        if self.mode == "multiplayer":
            if (self.is_host and player_index != 0) or (not self.is_host and player_index != 1):
                return

        current_pos = self.positions[player_index]
        new_pos = current_pos + self.dice_value

        # Check for overshoot
        if new_pos > 100:
            self.status_label.config(text="Overshot! Turn passes.")
            self.next_turn()
            return

        # Start move animation
        self.moving = True
        self.move_count[player_index] += 1
        self.animate_token_move(player_index, current_pos, new_pos)

    def animate_token_move(self, player_index, start_pos, end_pos, step=0):
        """Animate token movement"""
        total_steps = end_pos - start_pos

        if step < total_steps:
            # Move one step
            self.positions[player_index] = start_pos + step + 1
            self.update_token_positions()
            self.window.after(150, lambda: self.animate_token_move(player_index, start_pos, end_pos, step + 1))
        else:
            # Move complete, check for snakes/ladders
            final_pos = end_pos

            if final_pos in LADDERS:
                ladder_top = LADDERS[final_pos]
                self.status_label.config(text=f"{self.player_names[player_index]} climbed a ladder!")
                self.window.after(500, lambda: self.handle_special_move(player_index, ladder_top))
            elif final_pos in SNAKES:
                snake_tail = SNAKES[final_pos]
                self.status_label.config(text=f"{self.player_names[player_index]} hit a snake!")
                self.window.after(500, lambda: self.handle_special_move(player_index, snake_tail))
            else:
                self.complete_move(player_index, final_pos)

    def handle_special_move(self, player_index, new_pos):
        """Handle snake or ladder move"""
        self.positions[player_index] = new_pos
        self.update_token_positions()
        self.complete_move(player_index, new_pos)

    def complete_move(self, player_index, final_pos):
        """Complete a player move"""
        self.moving = False
        self.dice_value = 0

        # Send move to opponent in multiplayer
        if self.mode == "multiplayer" and self.websocket_connection:
            self.send_network_message({
                "type": "move",
                "player": player_index,
                "position": final_pos
            })

        # Check for win
        if final_pos >= 100:
            self.handle_game_end(player_index)
        else:
            self.next_turn()

    def next_turn(self):
        """Switch to next player's turn"""
        self.current_player = 1 - self.current_player
        self.update_ui_state()

        # Send turn change in multiplayer
        if self.mode == "multiplayer" and self.websocket_connection:
            self.send_network_message({
                "type": "turn_change",
                "current_player": self.current_player
            })

    def handle_game_end(self, winner_index):
        """Handle game end"""
        self.game_over = True
        winner_name = self.player_names[winner_index]
        game_duration = int(time.time() - self.start_time)

        self.status_label.config(text=f"🏆 {winner_name} WINS! 🏆")
        self.roll_button.config(state=tk.DISABLED)

        # Save statistics for solo games
        if self.mode == "solo":
            self.save_local_stats(winner_index == 0, game_duration)

        # Show victory message
        result = messagebox.askquestion(
            "Game Over",
            f"🏆 {winner_name} wins!\n"
            f"Game duration: {game_duration}s\n"
            f"Moves: P1={self.move_count[0]}, P2={self.move_count[1]}\n\n"
            "Play again?",
            icon='question'
        )

        if result == "yes":
            self.reset_game()
        else:
            self.quit_game()

    def save_local_stats(self, player_won, duration):
        """Save local game statistics"""
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
            print(f"Error saving stats: {e}")

    def update_ui_state(self):
        """Update UI based on current game state"""
        if self.game_over:
            return

        # Update player label highlighting
        for i, label in enumerate(self.player_labels):
            if i == self.current_player:
                label.config(font=("Arial", 12, "bold"), relief=tk.RAISED)
            else:
                label.config(font=("Arial", 12, "normal"), relief=tk.FLAT)

        # Update status and button state
        if self.mode == "multiplayer":
            if (self.is_host and self.current_player == 0) or (not self.is_host and self.current_player == 1):
                self.status_label.config(text="Your turn - Roll the dice!")
                self.roll_button.config(state=tk.NORMAL)
            else:
                opponent_name = self.player_names[1 - self.current_player] if self.is_host else self.player_names[
                    self.current_player]
                self.status_label.config(text=f"Waiting for {opponent_name}...")
                self.roll_button.config(state=tk.DISABLED)
        else:  # Solo mode
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

        # Send reset message in multiplayer
        if self.mode == "multiplayer" and self.websocket_connection:
            self.send_network_message({"type": "reset"})

    def quit_game(self):
        """Quit the game"""
        if callable(self.on_game_end):
            self.on_game_end(None)
        self.window.destroy()

    # Network communication methods
    def send_network_message(self, data):
        """Send message through network connection"""
        if self.websocket_connection:
            try:
                return self.websocket_connection.send_message(data)
            except Exception as e:
                print(f"Network send error: {e}")
                return False
        return False

    def handle_network_message(self, data):
        """Handle incoming network message"""
        try:
            msg_type = data.get("type")

            if msg_type == "dice_roll":
                player = data.get("player")
                value = data.get("value")
                if player != (0 if self.is_host else 1):  # From opponent
                    self.dice_value = value
                    dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
                    self.dice_label.config(text=dice_faces[value - 1])
                    self.status_label.config(text=f"{self.player_names[player]} rolled {value}!")

            elif msg_type == "move":
                player = data.get("player")
                position = data.get("position")
                if player != (0 if self.is_host else 1):  # From opponent
                    self.positions[player] = position
                    self.update_token_positions()

            elif msg_type == "turn_change":
                self.current_player = data.get("current_player")
                self.update_ui_state()

            elif msg_type == "reset":
                self.reset_game()

        except Exception as e:
            print(f"Network message handling error: {e}")

    def handle_disconnect(self):
        """Handle opponent disconnection"""
        self.status_label.config(text="Opponent disconnected!")
        self.roll_button.config(state=tk.DISABLED)
        messagebox.showinfo("Disconnected", "The other player has disconnected.")

    def check_network_messages(self):
        """Periodically check for network messages (for multiplayer)"""
        if self.mode == "multiplayer" and not self.game_over:
            # This would be called periodically to check for messages
            # In the actual implementation, this would be handled by the WebSocket connection
            pass

        if not self.game_over:
            self.window.after(100, self.check_network_messages)


if __name__ == "__main__":
    # Test the game standalone
    root = tk.Tk()
    game = SnakeLadderGame(
        root,
        player_names=["Player", "Bot"],
        player_avatars=["🙂", "🤖"],
        mode="solo"
    )
    root.mainloop()