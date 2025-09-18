#!/usr/bin/env python3
"""
Fixed Snake & Ladder Game Core Logic
Properly handles multiplayer synchronization and shows opponent actions
"""

import tkinter as tk
from tkinter import messagebox
import random
import json
import time
import os
import math
import asyncio
import threading

# Game constants
BOARD_SIZE = 640
TILE_SIZE = BOARD_SIZE // 10
BOARD_MARGIN = 40

# Snakes and ladders positions
SNAKES = {98: 78, 95: 56, 87: 24, 62: 18, 54: 34, 16: 6}
LADDERS = {1: 38, 4: 14, 9: 21, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100}


class SnakeLadderGame:
    """Main game class for Snake & Ladder with proper multiplayer sync and opponent action visibility"""

    def __init__(self, window, player_names, player_avatars, mode="solo",
                 websocket_connection=None, is_host=True, my_player_index=0, on_game_end=None):

        self.window = window
        self.window.title("Snake & Ladder Game")
        self.window.configure(bg="#2c3e50")

        # Game parameters
        self.player_names = player_names or ["Player 1", "Player 2"]
        self.player_avatars = player_avatars or ["🙂", "😎"]
        self.mode = mode  # "solo", "multiplayer"
        self.websocket_connection = websocket_connection
        self.is_host = is_host
        self.my_player_index = my_player_index  # Which player this client controls
        self.on_game_end = on_game_end

        # Game state
        self.positions = [0, 0]
        self.dice_value = 0
        self.current_player = 0  # Always start with player 0 (host)
        self.game_over = False

        # For multiplayer: determine if it's my turn
        self.my_turn = (self.current_player == self.my_player_index)

        # Animation state
        self.moving = False
        self.dice_rolling = False

        # Statistics
        self.start_time = time.time()
        self.move_count = [0, 0]

        # Network message queue for thread safety
        self.message_queue = []
        self.queue_lock = threading.Lock()

        print(f"Game initialized - Mode: {mode}, My player: {my_player_index}, Is host: {is_host}")
        print(f"Player names: {self.player_names}")
        print(f"My turn: {self.my_turn}")

        # Initialize UI
        self.setup_ui()
        self.create_board()
        self.create_tokens()
        self.update_ui_state()

        # Start message processing for multiplayer
        if mode == "multiplayer":
            self.process_network_messages()

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
            # Highlight my player with a special indicator
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

            # Bind click events - only allow clicking on your own token in multiplayer
            if self.mode == "solo":
                # In solo mode, allow clicking any token on appropriate turn
                self.canvas.tag_bind(f"player{i}", "<Button-1>",
                                     lambda e, p=i: self.try_move_token(p))
            elif self.mode == "multiplayer":
                # In multiplayer, only allow clicking own token
                if i == self.my_player_index:
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
            print("Cannot roll dice - game state prevents it")
            return

        # Check if it's player's turn
        if self.mode == "multiplayer":
            if not self.my_turn:
                self.status_label.config(text="Wait for your turn!")
                print(f"Not my turn - current player: {self.current_player}, my index: {self.my_player_index}")
                return
        elif self.mode == "solo":
            # In solo mode, human player can only roll on their turn (player 0)
            if self.current_player != 0:
                print(f"Solo mode - not player 0's turn (current: {self.current_player})")
                return

        print(f"Rolling dice - Current player: {self.current_player}, My index: {self.my_player_index}")

        self.dice_rolling = True
        self.roll_button.config(state=tk.DISABLED)
        self.animate_dice_roll()

    def animate_dice_roll(self, frame=0, final_value=None):
        """Animate dice rolling - can be used for both local and opponent rolls"""
        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

        if frame < 10:
            # Show random dice face during animation
            random_face = random.choice(dice_faces)
            self.dice_label.config(text=random_face)
            self.window.after(100, lambda: self.animate_dice_roll(frame + 1, final_value))
        else:
            # Final dice value
            if final_value is None:
                # This is a local roll
                self.dice_value = random.randint(1, 6)
                final_value = self.dice_value

                # Send dice roll to opponent in multiplayer
                if self.mode == "multiplayer" and self.websocket_connection:
                    success = self.send_network_message({
                        "type": "dice_roll",
                        "player": self.current_player,
                        "value": self.dice_value
                    })
                    print(f"Sent dice roll message: {success}")
            else:
                # This is showing opponent's roll
                self.dice_value = final_value

            self.dice_label.config(text=dice_faces[final_value - 1])
            self.dice_rolling = False
            self.status_label.config(text=f"{self.player_names[self.current_player]} rolled {final_value}!")

            print(f"Dice animation complete: {final_value} by player {self.current_player}")

            # Enable move for current player or auto-move for bot
            if self.mode == "solo" and self.current_player == 1:
                # Auto-move for bot in solo mode
                self.window.after(1000, lambda: self.try_move_token(1))
            elif self.mode == "multiplayer":
                if self.my_turn:
                    self.status_label.config(text=f"Click your token to move {final_value} spaces!")
                else:
                    self.status_label.config(text=f"Opponent is moving {final_value} spaces...")
            else:
                self.status_label.config(text=f"Click your token to move {final_value} spaces!")

    def try_move_token(self, player_index):
        """Try to move a token"""
        if (self.game_over or self.moving or self.dice_rolling or
                self.dice_value == 0):
            print(f"Cannot move token - game state prevents it (dice: {self.dice_value})")
            return

        # Check if it's the correct player's turn
        if player_index != self.current_player:
            print(f"Wrong player trying to move: {player_index}, current: {self.current_player}")
            return

        # In multiplayer, check if it's the correct player's turn
        if self.mode == "multiplayer":
            if not self.my_turn:
                print(f"Not my turn: trying {player_index}, my index: {self.my_player_index}")
                return

        current_pos = self.positions[player_index]
        new_pos = current_pos + self.dice_value

        print(f"Moving player {player_index} from {current_pos} to {new_pos}")

        # Check for overshoot
        if new_pos > 100:
            self.status_label.config(text="Overshot! Turn passes.")
            # Still need to switch turns even on overshoot
            if self.mode == "multiplayer":
                self.next_turn()
            else:
                self.next_turn()
            return

        # Start move animation
        self.moving = True
        self.move_count[player_index] += 1
        self.animate_token_move(player_index, current_pos, new_pos)

    def animate_token_move(self, player_index, start_pos, end_pos, step=0, is_opponent_move=False):
        """Animate token movement - works for both local and opponent moves"""
        total_steps = end_pos - start_pos

        if step < total_steps:
            # Move one step
            self.positions[player_index] = start_pos + step + 1
            self.update_token_positions()
            self.window.after(150, lambda: self.animate_token_move(player_index, start_pos, end_pos, step + 1,
                                                                   is_opponent_move))
        else:
            # Move complete, check for snakes/ladders
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
        """Handle snake or ladder move"""
        self.positions[player_index] = new_pos
        self.update_token_positions()
        self.complete_move(player_index, new_pos, is_opponent_move)

    def complete_move(self, player_index, final_pos, is_opponent_move=False):
        """Complete a player move"""
        self.moving = False
        self.dice_value = 0

        print(f"Move completed - Player {player_index} at position {final_pos}")

        # Send move to opponent in multiplayer (only if this is our move)
        if self.mode == "multiplayer" and self.websocket_connection and not is_opponent_move:
            success = self.send_network_message({
                "type": "move_complete",
                "player": player_index,
                "position": final_pos,
                "move_count": self.move_count[player_index]
            })
            print(f"Sent move complete message: {success}")

        # Check for win
        if final_pos >= 100:
            self.handle_game_end(player_index)
        else:
            # Only switch turns if this is our move (not opponent's move)
            if not is_opponent_move:
                self.next_turn()
            else:
                # For opponent moves, just update UI state
                self.update_ui_state()

    def next_turn(self):
        """Switch to next player's turn"""
        self.current_player = 1 - self.current_player
        self.dice_value = 0  # Reset dice value

        if self.mode == "multiplayer":
            self.my_turn = (self.current_player == self.my_player_index)

        print(f"Turn changed to player {self.current_player} (My turn: {self.my_turn})")

        self.update_ui_state()

        # Send turn change in multiplayer (only the player who completed the move sends this)
        if self.mode == "multiplayer" and self.websocket_connection:
            success = self.send_network_message({
                "type": "turn_change",
                "current_player": self.current_player
            })
            print(f"Sent turn change message: {success}")

        # Auto-roll for bot in solo mode
        if self.mode == "solo" and self.current_player == 1:
            self.window.after(1000, self.roll_dice)

    def handle_game_end(self, winner_index):
        """Handle game end"""
        self.game_over = True
        winner_name = self.player_names[winner_index]
        game_duration = int(time.time() - self.start_time)

        self.status_label.config(text=f"🏆 {winner_name} WINS! 🏆")
        self.roll_button.config(state=tk.DISABLED)

        print(f"Game ended - Winner: {winner_name} (Player {winner_index})")

        # Send game end to opponent in multiplayer
        if self.mode == "multiplayer" and self.websocket_connection:
            success = self.send_network_message({
                "type": "game_end",
                "winner": winner_index
            })
            print(f"Sent game end message: {success}")

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
            if self.my_turn:
                self.status_label.config(text="Your turn - Roll the dice!")
                self.roll_button.config(state=tk.NORMAL)
            else:
                opponent_name = self.player_names[1 - self.my_player_index]
                self.status_label.config(text=f"Waiting for {opponent_name}...")
                self.roll_button.config(state=tk.DISABLED)
        else:  # Solo mode
            if self.current_player == 0:
                self.status_label.config(text=f"{self.player_names[self.current_player]}'s turn")
                self.roll_button.config(state=tk.NORMAL)
            else:
                self.status_label.config(text=f"{self.player_names[self.current_player]}'s turn (Bot)")
                self.roll_button.config(state=tk.DISABLED)

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

        # Reset turn state for multiplayer
        if self.mode == "multiplayer":
            self.my_turn = (self.current_player == self.my_player_index)

        self.dice_label.config(text="🎲")
        self.update_token_positions()
        self.update_ui_state()

        print("Game reset")

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
            return self.websocket_connection.send_message(data)
        return False

    def handle_network_message(self, data):
        """Handle incoming network message - queue for thread-safe processing"""
        with self.queue_lock:
            self.message_queue.append(data)

    def process_network_messages(self):
        """Process queued network messages in UI thread"""
        try:
            with self.queue_lock:
                messages_to_process = self.message_queue.copy()
                self.message_queue.clear()

            for data in messages_to_process:
                self._process_single_message(data)

        except Exception as e:
            print(f"Error processing network messages: {e}")

        # Schedule next processing
        if not self.game_over:
            self.window.after(100, self.process_network_messages)

    def _process_single_message(self, data):
        """Process a single network message"""
        try:
            msg_type = data.get("type")
            print(f"Processing network message: {data}")

            if msg_type == "dice_roll":
                player = data.get("player")
                value = data.get("value")
                # Only process if it's from the opponent
                if player != self.my_player_index:
                    print(f"Showing opponent's dice roll: {value}")
                    self.dice_rolling = True
                    self.roll_button.config(state=tk.DISABLED)
                    # Show the dice roll animation with the opponent's value
                    self.animate_dice_roll(final_value=value)

            elif msg_type == "move_complete":
                player = data.get("player")
                position = data.get("position")
                move_count = data.get("move_count", 0)

                # Only process if it's from the opponent
                if player != self.my_player_index:
                    print(f"Processing opponent move from {self.positions[player]} to {position}")
                    old_pos = self.positions[player]
                    self.move_count[player] = move_count

                    # Show the movement animation for opponent
                    if old_pos != position:
                        self.moving = True
                        self.animate_token_move(player, old_pos, position, is_opponent_move=True)
                    else:
                        # Direct position update if no animation needed
                        self.positions[player] = position
                        self.update_token_positions()

            elif msg_type == "turn_change":
                new_current_player = data.get("current_player")
                # Only update if it's actually a different player
                if new_current_player != self.current_player:
                    self.current_player = new_current_player
                    self.my_turn = (self.current_player == self.my_player_index)
                    self.dice_value = 0  # Reset dice value
                    self.update_ui_state()
                    print(f"Turn changed via network to player {new_current_player} (My turn: {self.my_turn})")
                else:
                    print(f"Received redundant turn change message for player {new_current_player}")

            elif msg_type == "reset":
                self.reset_game()

            elif msg_type == "game_end":
                winner = data.get("winner")
                if not self.game_over:  # Only process if game isn't already ended locally
                    self.handle_game_end(winner)

        except Exception as e:
            print(f"Error processing single network message: {e}")

    def handle_disconnect(self):
        """Handle opponent disconnection"""
        self.status_label.config(text="Opponent disconnected!")
        self.roll_button.config(state=tk.DISABLED)
        messagebox.showinfo("Disconnected", "The other player has disconnected.")


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