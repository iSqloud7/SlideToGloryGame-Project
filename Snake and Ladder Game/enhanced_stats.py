# enhanced_stats.py - Enhanced statistics system for Snake and Ladder Game

import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional


class StatsManager:
    """Manages both local (session-based) and global (all-time) statistics"""

    def __init__(self, username: str = None):
        self.username = username
        self.local_stats_file = f"local_stats_{username}.json" if username else "local_stats.json"
        self.global_stats_file = f"global_stats_{username}.json" if username else "global_stats.json"

        # Initialize default stats structure
        self.default_stats = {
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "fastest_win": None,
            "longest_game": None,
            "win_streak": 0,
            "best_win_streak": 0,
            "total_playtime": 0,
            "last_played": None,
            "session_start": None,
            "session_games": 0,
            "session_wins": 0
        }

        # Load existing stats
        self.local_stats = self.load_stats(self.local_stats_file)
        self.global_stats = self.load_stats(self.global_stats_file)

        # Initialize session if not exists
        if not self.local_stats.get("session_start"):
            self.start_new_session()

    def load_stats(self, filename: str) -> Dict[str, Any]:
        """Load statistics from file or create default if not exists"""
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    loaded_stats = json.load(f)
                    # Merge with default stats to ensure all keys exist
                    stats = self.default_stats.copy()
                    stats.update(loaded_stats)
                    return stats
            except Exception as e:
                print(f"Error loading {filename}: {e}")

        return self.default_stats.copy()

    def save_stats(self, stats: Dict[str, Any], filename: str) -> bool:
        """Save statistics to file"""
        try:
            with open(filename, 'w') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving {filename}: {e}")
            return False

    def start_new_session(self):
        """Start a new local session"""
        self.local_stats["session_start"] = datetime.now().isoformat()
        self.local_stats["session_games"] = 0
        self.local_stats["session_wins"] = 0
        self.save_stats(self.local_stats, self.local_stats_file)
        print("New session started!")

    def record_game(self, won: bool, game_duration: int, opponent: str = "Bot"):
        """Record a game result in both local and global stats"""
        now = datetime.now().isoformat()

        # Update both local and global stats
        for stats in [self.local_stats, self.global_stats]:
            stats["games_played"] += 1
            stats["last_played"] = now
            stats["total_playtime"] += game_duration

            if won:
                stats["wins"] += 1
                stats["win_streak"] += 1

                # Update best win streak
                if stats["win_streak"] > stats["best_win_streak"]:
                    stats["best_win_streak"] = stats["win_streak"]

                # Update fastest win
                if stats["fastest_win"] is None or game_duration < stats["fastest_win"]:
                    stats["fastest_win"] = game_duration
            else:
                stats["losses"] += 1
                stats["win_streak"] = 0  # Reset win streak on loss

            # Update longest game
            if stats["longest_game"] is None or game_duration > stats["longest_game"]:
                stats["longest_game"] = game_duration

        # Update session-specific stats
        self.local_stats["session_games"] += 1
        if won:
            self.local_stats["session_wins"] += 1

        # Save both files
        self.save_stats(self.local_stats, self.local_stats_file)
        self.save_stats(self.global_stats, self.global_stats_file)

        print(f"Game recorded: {'Win' if won else 'Loss'} in {game_duration}s")

        # Check for session milestone (5 wins)
        if self.local_stats["session_wins"] >= 5:
            self.complete_session()

    def complete_session(self):
        """Complete current session and start a new one"""
        session_games = self.local_stats["session_games"]
        session_wins = self.local_stats["session_wins"]

        print(f"Session completed! {session_wins}/{session_games} wins")

        # Archive this session
        session_summary = {
            "start_time": self.local_stats["session_start"],
            "end_time": datetime.now().isoformat(),
            "games": session_games,
            "wins": session_wins,
            "win_rate": round((session_wins / session_games) * 100, 1) if session_games > 0 else 0
        }

        # Save session history
        self.save_session_history(session_summary)

        # Start new session
        self.start_new_session()

    def save_session_history(self, session_summary: Dict[str, Any]):
        """Save completed session to history"""
        history_file = f"session_history_{self.username}.json" if self.username else "session_history.json"

        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {"sessions": []}

            history["sessions"].append(session_summary)

            # Keep only last 50 sessions
            if len(history["sessions"]) > 50:
                history["sessions"] = history["sessions"][-50:]

            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Error saving session history: {e}")

    def get_local_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        stats = self.local_stats.copy()

        # Calculate session progress
        session_progress = min(stats["session_wins"], 5)
        stats["session_progress"] = f"{session_progress}/5 wins"
        stats["session_complete"] = session_progress >= 5

        return stats

    def get_global_stats(self) -> Dict[str, Any]:
        """Get all-time statistics"""
        return self.global_stats.copy()

    def get_display_stats(self) -> Dict[str, str]:
        """Get formatted statistics for display"""
        local = self.local_stats
        global_stats = self.global_stats

        # Format durations
        def format_duration(seconds):
            if seconds is None:
                return "N/A"
            if seconds < 60:
                return f"{seconds}s"
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds}s"

        return {
            # Current session
            "session_progress": f"{local['session_wins']}/5 wins",
            "session_games": str(local['session_games']),
            "session_win_rate": f"{round((local['session_wins'] / local['session_games']) * 100, 1)}%" if local[
                                                                                                              'session_games'] > 0 else "0%",

            # Global stats
            "total_games": str(global_stats['games_played']),
            "total_wins": str(global_stats['wins']),
            "total_losses": str(global_stats['losses']),
            "overall_win_rate": f"{round((global_stats['wins'] / global_stats['games_played']) * 100, 1)}%" if
            global_stats['games_played'] > 0 else "0%",
            "fastest_win": format_duration(global_stats['fastest_win']),
            "longest_game": format_duration(global_stats['longest_game']),
            "best_win_streak": str(global_stats['best_win_streak']),
            "current_win_streak": str(global_stats['win_streak']),
            "total_playtime": format_duration(global_stats['total_playtime'])
        }

    def reset_session(self):
        """Reset current session (for testing or manual reset)"""
        self.start_new_session()
        print("Session reset!")

    def reset_global_stats(self):
        """Reset all-time statistics (dangerous operation)"""
        self.global_stats = self.default_stats.copy()
        self.save_stats(self.global_stats, self.global_stats_file)
        print("Global statistics reset!")


def sync_stats_with_server(stats_manager: StatsManager, server_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Sync local global stats with server stats, taking the higher values"""
    if not server_stats:
        return stats_manager.get_global_stats()

    local_global = stats_manager.global_stats

    # Create merged stats taking the maximum values for cumulative stats
    merged_stats = {
        "games_played": max(server_stats.get("games_played", 0), local_global.get("games_played", 0)),
        "wins": max(server_stats.get("wins", 0), local_global.get("wins", 0)),
        "losses": max(server_stats.get("losses", 0), local_global.get("losses", 0)),
    }

    # For fastest_win, take the better (lower) time if both exist
    server_fastest = server_stats.get("fastest_win")
    local_fastest = local_global.get("fastest_win")

    if server_fastest is not None and local_fastest is not None:
        merged_stats["fastest_win"] = min(server_fastest, local_fastest)
    elif server_fastest is not None:
        merged_stats["fastest_win"] = server_fastest
    elif local_fastest is not None:
        merged_stats["fastest_win"] = local_fastest
    else:
        merged_stats["fastest_win"] = None

    # Update other stats
    merged_stats["longest_game"] = max(
        server_stats.get("longest_game", 0) or 0,
        local_global.get("longest_game", 0) or 0
    )
    merged_stats["best_win_streak"] = max(
        server_stats.get("best_win_streak", 0),
        local_global.get("best_win_streak", 0)
    )
    merged_stats["total_playtime"] = max(
        server_stats.get("total_playtime", 0),
        local_global.get("total_playtime", 0)
    )

    # Current win streak and last played from server (more recent)
    merged_stats["win_streak"] = server_stats.get("win_streak", local_global.get("win_streak", 0))
    merged_stats["last_played"] = server_stats.get("last_played", local_global.get("last_played"))

    # Update the stats manager's global stats
    stats_manager.global_stats.update(merged_stats)
    stats_manager.save_stats(stats_manager.global_stats, stats_manager.global_stats_file)

    return merged_stats