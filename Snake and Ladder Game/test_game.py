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
        ('asyncio', 'Async support')
    ]

    optional_modules = [
        ('websockets', 'WebSocket support'),
        ('fastapi', 'Auth server'),
        ('uvicorn', 'Web server'),
        ('requests', 'HTTP client')
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
        ('utils.py', 'Utilities')
    ]

    all_ok = True

    for filename, desc in required_files:
        if os.path.exists(filename):
            print(f"✅ {filename} - {desc}")
        else:
            print(f"❌ {filename} - {desc} (MISSING)")
            all_ok = False

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


def test_json_operations():
    print("Testing JSON operations...")

    try:
        test_data = {
            "username": "testuser",
            "stats": {"wins": 5, "losses": 2},
            "profile": {"avatar": "🎮", "name": "Tester"}
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

        return True

    except Exception as e:
        print(f"❌ Game constants test failed: {e}")
        return False


def test_tkinter_gui():
    print("Testing GUI framework...")

    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()

        frame = tk.Frame(root)
        label = tk.Label(frame, text="Test")
        button = tk.Button(frame, text="Test Button")
        entry = tk.Entry(frame)

        print("✅ Tkinter GUI framework works")
        root.destroy()
        return True

    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        return False


def test_network_modules():
    print("Testing network modules...")

    try:
        import asyncio

        async def test_async():
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
    except ImportError:
        print("⚠️  WebSockets not available (needed for multiplayer)")

    return True


def run_all_tests():
    print("=" * 50)
    print("Snake & Ladder Game - Test Suite")
    print("=" * 50)

    tests = [
        test_python_version,
        test_imports,
        test_file_structure,
        test_utils,
        test_json_operations,
        test_game_constants,
        test_tkinter_gui,
        test_network_modules
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
    else:
        print("⚠️  Some tests failed. Check missing dependencies.")
        if any(['websockets' in str(e) for e in sys.modules]):
            print("For full functionality, install: pip install websockets fastapi uvicorn requests")

    return failed == 0


if __name__ == "__main__":
    run_all_tests()