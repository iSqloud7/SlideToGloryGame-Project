import json
import os
import hashlib
import platform
import subprocess
import sys


def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def load_json_file(filename, default=None):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")

    return default if default is not None else {}


def save_json_file(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {filename}: {e}")
        return False


def validate_username(username):
    username = username.strip()

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 20:
        return False, "Username must be less than 20 characters"

    invalid_chars = ['<', '>', '"', "'", '&', '/', '\\', ' ']
    for char in invalid_chars:
        if char in username:
            return False, f"Username cannot contain '{char}'"

    return True, "Valid"


def validate_password(password):
    password = password.strip()

    if len(password) < 4:
        return False, "Password must be at least 4 characters"

    if len(password) > 50:
        return False, "Password must be less than 50 characters"

    return True, "Valid"


def get_system_info():
    return {
        "platform": platform.system(),
        "version": platform.release(),
        "python_version": sys.version,
        "architecture": platform.architecture()[0]
    }


def check_port_available(host, port):
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result != 0
    except:
        return False


def kill_process_on_port(port):
    try:
        system = platform.system().lower()

        if system == "windows":
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True, capture_output=True, text=True
            )

            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) > 4:
                            pid = parts[-1]
                            subprocess.run(f'taskkill /PID {pid} /F', shell=True)
                            return True

        else:
            result = subprocess.run(
                f'lsof -ti:{port}',
                shell=True, capture_output=True, text=True
            )

            if result.stdout:
                pid = result.stdout.strip()
                subprocess.run(f'kill -9 {pid}', shell=True)
                return True

    except Exception as e:
        print(f"Error killing process on port {port}: {e}")

    return False


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"


def generate_invite_code(length=8):
    import random
    import string

    characters = string.ascii_uppercase + string.digits
    characters = characters.replace('0', '').replace('O', '').replace('I', '').replace('1')

    return ''.join(random.choice(characters) for _ in range(length))


def validate_invite_code(code):
    if not code or len(code) != 8:
        return False

    allowed = set('ABCDEFGHJKLMNPQRSTUVWXYZ23456789')
    return all(c.upper() in allowed for c in code)


def clean_filename(filename):
    import re

    cleaned = re.sub(r'[<>:"/\\|?*]', '', filename)

    cleaned = cleaned.replace(' ', '_')

    if len(cleaned) > 50:
        cleaned = cleaned[:50]

    return cleaned


def get_local_ip():
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"


def test_network_connectivity(host="8.8.8.8", port=53, timeout=3):
    import socket
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except:
        return False


def create_backup_file(filename):
    if os.path.exists(filename):
        backup_name = f"{filename}.backup"
        try:
            import shutil
            shutil.copy2(filename, backup_name)
            return backup_name
        except Exception as e:
            print(f"Error creating backup: {e}")
    return None


def log_error(error_message, filename="error.log"):
    import datetime

    try:
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f"[{timestamp}] {error_message}\n"

        with open(filename, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error logging to file: {e}")


def ensure_directory(path):
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {path}: {e}")
        return False


def get_file_size_mb(filename):
    try:
        size_bytes = os.path.getsize(filename)
        return round(size_bytes / (1024 * 1024), 2)
    except:
        return 0


def cleanup_old_files(directory, max_age_days=30, pattern="*.log"):
    import glob
    import datetime

    try:
        pattern_path = os.path.join(directory, pattern)
        files = glob.glob(pattern_path)

        cutoff_time = datetime.datetime.now() - datetime.timedelta(days=max_age_days)
        removed_count = 0

        for file_path in files:
            file_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_time < cutoff_time:
                os.remove(file_path)
                removed_count += 1

        return removed_count

    except Exception as e:
        print(f"Error cleaning up files: {e}")
        return 0


class SimpleConfig:

    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load()

    def load(self):
        return load_json_file(self.config_file, {})

    def save(self):
        return save_json_file(self.config_file, self.config)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        return self.save()

    def update(self, updates):
        self.config.update(updates)
        return self.save()


class GameStats:
    def __init__(self, stats_file="game_stats.json"):
        self.stats_file = stats_file
        self.stats = self.load()

    def load(self):
        default_stats = {
            "total_games": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "total_time": 0,
            "best_time": None,
            "worst_time": None,
            "avg_moves": 0,
            "last_played": None
        }
        return load_json_file(self.stats_file, default_stats)

    def save(self):
        return save_json_file(self.stats_file, self.stats)

    def add_game(self, result, duration, moves):
        import datetime

        self.stats["total_games"] += 1
        self.stats["total_time"] += duration
        self.stats["last_played"] = datetime.datetime.now().isoformat()

        if result == "win":
            self.stats["wins"] += 1
        elif result == "loss":
            self.stats["losses"] += 1
        else:
            self.stats["draws"] += 1

        if self.stats["best_time"] is None or duration < self.stats["best_time"]:
            self.stats["best_time"] = duration

        if self.stats["worst_time"] is None or duration > self.stats["worst_time"]:
            self.stats["worst_time"] = duration

        total_moves = self.stats.get("total_moves", 0) + moves
        self.stats["total_moves"] = total_moves
        self.stats["avg_moves"] = round(total_moves / self.stats["total_games"], 1)

        return self.save()

    def get_win_rate(self):
        if self.stats["total_games"] == 0:
            return 0
        return round((self.stats["wins"] / self.stats["total_games"]) * 100, 1)

    def get_summary(self):
        if self.stats["total_games"] == 0:
            return "No games played yet"

        win_rate = self.get_win_rate()
        avg_time = self.stats["total_time"] / self.stats["total_games"]

        return (f"Games: {self.stats['total_games']} | "
                f"Win Rate: {win_rate}% | "
                f"Best Time: {format_duration(self.stats['best_time'] or 0)} | "
                f"Avg Time: {format_duration(int(avg_time))}")


def print_system_info():
    info = get_system_info()
    print("=== System Information ===")
    print(f"Platform: {info['platform']} {info['version']}")
    print(f"Python: {info['python_version']}")
    print(f"Architecture: {info['architecture']}")
    print(f"Local IP: {get_local_ip()}")
    print(f"Network: {'Connected' if test_network_connectivity() else 'Disconnected'}")


if __name__ == "__main__":
    print("Testing utility functions...")

    config = SimpleConfig("test_config.json")
    config.set("test_key", "test_value")
    print(f"Config test: {config.get('test_key')}")

    stats = GameStats("test_stats.json")
    stats.add_game("win", 120, 25)
    print(f"Stats test: {stats.get_summary()}")

    print(f"Duration format: {format_duration(125)}")
    print(f"Invite code: {generate_invite_code()}")

    for file in ["test_config.json", "test_stats.json"]:
        if os.path.exists(file):
            os.remove(file)

    print("Utility tests completed!")