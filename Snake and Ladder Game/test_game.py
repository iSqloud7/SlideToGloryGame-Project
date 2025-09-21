import sys
import os
import json
import tempfile
import shutil


def test_python_version():
    print("Testing Python version...")
    if sys.version_info >= (3, 8):
        print("✅ Python version OK")
        return True
    else:
        print(f"❌ Python version {sys.version} too old (need 3.8+)")
        return False


def test_imports():
    print("Testing imports...")

    required_modules = [
        ('tkinter', 'GUI framework'),
        ('json', 'JSON handling'),
        ('hashlib', 'Password hashing'),
        ('threading', 'Threading support'),
        ('asyncio', 'Async support'),
        ('datetime', 'Date/time handling')
    ]

    optional_modules = [
        ('websockets', 'WebSocket support'),
        ('fastapi', 'Auth server'),
        ('uvicorn', 'Web server'),
        ('requests', 'HTTP client'),
        ('pygame', 'Music/audio system'),
        ('playsound', 'Simple audio playback'),
        ('pydub', 'Audio processing'),
        ('mutagen', 'Audio metadata')
    ]

    all_ok = True

    for module, desc in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} - {desc}")
        except ImportError:
            print(f"❌ {module} - {desc} (REQUIRED)")
            all_ok = False

    for module, desc in optional_modules:
        try:
            __import__(module)
            print(f"✅ {module} - {desc}")
        except ImportError:
            print(f"⚠️  {module} - {desc} (install with: pip install {module})")

    return all_ok


def test_file_structure():
    print("Testing file structure...")

    required_files = [
        ('main.py', 'Main launcher'),
        ('auth_server.py', 'Auth server'),
        ('websocket_server.py', 'WebSocket server'),
        ('game_client.py', 'Game client'),
        ('snake_ladder_core.py', 'Game logic'),
        ('utils.py', 'Utilities'),
        ('stats.py', 'Statistics manager')
    ]

    optional_files = [
        ('music_manager.py', 'Music system'),
        ('profile.json', 'User profile'),
        ('server_config.json', 'Server configuration')
    ]

    required_dirs = [
        ('data', 'Game data directory'),
        ('Music', 'Music files directory')
    ]

    all_ok = True

    for filename, desc in required_files:
        if os.path.exists(filename):
            print(f"✅ {filename} - {desc}")
        else:
            print(f"❌ {filename} - {desc} (MISSING)")
            all_ok = False

    for filename, desc in optional_files:
        if os.path.exists(filename):
            print(f"✅ {filename} - {desc}")
        else:
            print(f"ℹ️  {filename} - {desc} (optional)")

    for dirname, desc in required_dirs:
        if os.path.exists(dirname) and os.path.isdir(dirname):
            print(f"✅ {dirname}/ - {desc}")
        else:
            print(f"ℹ️  {dirname}/ - {desc} (will be created)")
            try:
                os.makedirs(dirname, exist_ok=True)
                print(f"✅ Created {dirname}/ directory")
            except Exception as e:
                print(f"⚠️  Could not create {dirname}/: {e}")

    return all_ok


def test_utils():
    print("Testing utilities...")

    try:
        from utils import (hash_password, validate_username, validate_password,
                           generate_invite_code, validate_invite_code)

        hashed = hash_password("test123")
        if len(hashed) == 64:
            print("✅ Password hashing works")
        else:
            print("❌ Password hashing failed")
            return False

        valid, msg = validate_username("testuser")
        if valid:
            print("✅ Username validation works")
        else:
            print(f"❌ Username validation failed: {msg}")
            return False

        code = generate_invite_code()
        if validate_invite_code(code):
            print("✅ Invite code generation works")
        else:
            print("❌ Invite code validation failed")
            return False

        return True

    except Exception as e:
        print(f"❌ Utils test failed: {e}")
        return False


def test_statistics_system():
    print("Testing statistics system...")

    try:
        from stats import StatsManager, sync_stats_with_server

        # Test stats manager creation
        stats_manager = StatsManager("test_user")
        print("✅ StatsManager creation works")

        # Test recording a game
        stats_manager.record_game(True, 120.5, "Bot")
        stats_manager.record_game(False, 180.0, "Player")
        print("✅ Game recording works")

        # Test getting display stats
        display_stats = stats_manager.get_display_stats()
        if isinstance(display_stats, dict) and 'total_games' in display_stats:
            print("✅ Display stats generation works")
        else:
            print("❌ Display stats generation failed")
            return False

        # Test session reset
        stats_manager.reset_session()
        print("✅ Session reset works")

        # Test sync function
        server_data = {"games_played": 5, "wins": 3, "losses": 2}
        merged = sync_stats_with_server(stats_manager, server_data)
        if isinstance(merged, dict):
            print("✅ Stats sync function works")
        else:
            print("❌ Stats sync function failed")
            return False

        return True

    except Exception as e:
        print(f"❌ Statistics test failed: {e}")
        return False


def test_music_system():
    print("Testing Music system...")

    try:
        from music_manager import (initialize_music, play_background_music,
                                   pause_music, resume_music, stop_music,
                                   toggle_music, set_volume, get_music_info)

        print("✅ Music system imports work")

        # Test Music manager initialization (might fail if no audio system)
        try:
            music_manager = initialize_music()
            if music_manager:
                print("✅ Music manager initialization works")

                # Test getting Music info
                info = get_music_info()
                if isinstance(info, dict) and 'status' in info:
                    print("✅ Music info retrieval works")
                else:
                    print("⚠️  Music info format unexpected")

                # Test volume setting
                set_volume(0.5)
                print("✅ Volume control works")

                # Test Music toggle
                toggle_music()
                print("✅ Music toggle works")

            else:
                print("⚠️  Music manager not initialized (no audio system?)")

        except Exception as e:
            print(f"⚠️  Music system test failed: {e} (audio system may not be available)")

        return True

    except ImportError:
        print("ℹ️  Music system not available (music_manager.py not found)")
        return True
    except Exception as e:
        print(f"❌ Music system test failed: {e}")
        return False


def test_json_operations():
    print("Testing JSON operations...")

    try:
        test_data = {
            "username": "testuser",
            "stats": {"wins": 5, "losses": 2, "session_wins": 2},
            "profile": {"avatar": "🎮", "name": "Tester"},
            "global_stats": {
                "games_played": 7,
                "wins": 5,
                "losses": 2,
                "fastest_win": 120.5,
                "total_playtime": 850.0
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            temp_file = f.name

        with open(temp_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

        if loaded_data == test_data:
            print("✅ JSON operations work")
            os.unlink(temp_file)
            return True
        else:
            print("❌ JSON data mismatch")
            os.unlink(temp_file)
            return False

    except Exception as e:
        print(f"❌ JSON test failed: {e}")
        return False


def test_game_constants():
    print("Testing game constants...")

    try:
        from snake_ladder_core import SNAKES, LADDERS

        if len(SNAKES) > 0 and all(head > tail for head, tail in SNAKES.items()):
            print("✅ Snakes configuration valid")
        else:
            print("❌ Snakes configuration invalid")
            return False

        if len(LADDERS) > 0 and all(bottom < top for bottom, top in LADDERS.items()):
            print("✅ Ladders configuration valid")
        else:
            print("❌ Ladders configuration invalid")
            return False

        snake_positions = set(SNAKES.keys()) | set(SNAKES.values())
        ladder_positions = set(LADDERS.keys()) | set(LADDERS.values())

        if not (snake_positions & ladder_positions):
            print("✅ No snake/ladder conflicts")
        else:
            print("⚠️  Snake/ladder position conflicts detected")

        # Test that positions are within valid board range
        all_positions = snake_positions | ladder_positions
        if all(1 <= pos <= 100 for pos in all_positions):
            print("✅ All positions within board range")
        else:
            print("❌ Some positions outside board range (1-100)")
            return False

        return True

    except Exception as e:
        print(f"❌ Game constants test failed: {e}")
        return False


def test_tkinter_gui():
    print("Testing GUI framework...")

    try:
        import tkinter as tk
        from tkinter import messagebox, simpledialog

        root = tk.Tk()
        root.withdraw()

        # Test basic widgets
        frame = tk.Frame(root)
        label = tk.Label(frame, text="Test")
        button = tk.Button(frame, text="Test Button")
        entry = tk.Entry(frame)
        canvas = tk.Canvas(frame, width=100, height=100)

        # Test advanced widgets
        scale = tk.Scale(frame, from_=0, to=100, orient=tk.HORIZONTAL)
        listbox = tk.Listbox(frame)
        radiobutton = tk.Radiobutton(frame, text="Test", value=1)

        print("✅ Tkinter GUI framework works")
        print("✅ Advanced GUI widgets available")

        root.destroy()
        return True

    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        return False


def test_network_modules():
    print("Testing network modules...")

    try:
        import asyncio
        import threading
        import inspect

        async def test_async():
            await asyncio.sleep(0.01)
            return "async works"

        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(test_async())
        loop.close()

        if result == "async works":
            print("✅ Asyncio works")
        else:
            print("❌ Asyncio failed")
            return False

    except Exception as e:
        print(f"❌ Asyncio test failed: {e}")
        return False

    try:
        import websockets
        print("✅ WebSockets available")

        # Test websockets signature inspection (used in game client)
        connect_sig = inspect.signature(websockets.connect)
        if 'extra_headers' in connect_sig.parameters:
            print("✅ WebSockets supports extra_headers")
        else:
            print("⚠️  WebSockets version may not support extra_headers")

    except ImportError:
        print("⚠️  WebSockets not available (needed for multiplayer)")

    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        # Test HTTP session creation
        session = requests.Session()
        retry_strategy = Retry(total=3, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        print("✅ HTTP client with retry logic works")

    except ImportError:
        print("⚠️  Requests not available (needed for auth server)")

    return True


def test_game_client_structure():
    print("Testing game client structure...")

    try:
        from game_client import GameClient, WebSocketConnection

        print("✅ GameClient class available")
        print("✅ WebSocketConnection class available")

        # Test that required methods exist
        required_methods = [
            'show_main_menu', 'show_welcome_screen', 'show_login_window',
            'show_register_window', 'show_profile', 'show_detailed_stats',
            'show_leaderboard', 'start_solo_game', 'host_multiplayer',
            'join_multiplayer', 'on_game_end'
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(GameClient, method):
                missing_methods.append(method)

        if not missing_methods:
            print("✅ All required GameClient methods present")
        else:
            print(f"❌ Missing GameClient methods: {missing_methods}")
            return False

        return True

    except Exception as e:
        print(f"❌ Game client structure test failed: {e}")
        return False


def run_all_tests():
    print("=" * 50)
    print("Snake & Ladder Game - Test Suite v2.0")
    print("=" * 50)

    tests = [
        test_python_version,
        test_imports,
        test_file_structure,
        test_utils,
        test_statistics_system,
        test_music_system,
        test_json_operations,
        test_game_constants,
        test_tkinter_gui,
        test_network_modules,
        test_game_client_structure
    ]

    passed = 0
    failed = 0

    for test in tests:
        print()
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1

    print()
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)

    if failed == 0:
        print("🎉 All tests passed! Game should work correctly.")
        print("Run 'python main.py' to start the game.")
    elif failed <= 2:
        print("⚠️  Minor issues detected but game should still work.")
        print("Consider installing optional dependencies for full functionality.")
        print("Run 'python main.py' to start the game.")
    else:
        print("❌ Multiple tests failed. Check missing dependencies.")
        print("\nTo install all optional dependencies:")
        print("pip install websockets fastapi uvicorn requests pygame playsound pydub mutagen")

    print("\n📁 Directory structure:")
    print("  - data/     : Game statistics and user data")
    print("  - Music/    : Music files for background audio")
    print("  - *.json    : Configuration and profile files")

    return failed == 0


if __name__ == "__main__":
    run_all_tests()