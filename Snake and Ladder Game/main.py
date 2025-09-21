import sys
import subprocess
import importlib
import threading
import time
import os
import platform
from pathlib import Path


def check_python_version():
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher required")
        print(f"   Current version: {sys.version}")
        return False
    return True


def check_and_install_dependencies():
    required_packages = {
        'websockets': 'websockets>=10.0',
        'fastapi': 'fastapi==0.104.1',
        'uvicorn': 'uvicorn==0.24.0',
        'requests': 'requests==2.31.0'
    }

    missing_packages = []

    for package, pip_name in required_packages.items():
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - missing")
            missing_packages.append(pip_name)

    if missing_packages:
        print(f"\n📦 Installing: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                                      sys.executable, "-m", "pip", "install"
                                  ] + missing_packages)
            print("✅ All packages installed!")
            return True
        except subprocess.CalledProcessError:
            print("❌ Installation failed. Try manually:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False

    return True


def check_required_files():
    required_files = [
        'auth_server.py',
        'websocket_server.py',
        'game_client.py',
        'snake_ladder_core.py'
    ]

    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            missing.append(file)
            print(f"❌ {file} - missing")

    if missing:
        print(f"\n❌ Missing files: {', '.join(missing)}")
        return False

    return True


def start_auth_server():
    try:
        print("🔄 Starting auth server...")

        if platform.system() == "Windows":
            process = subprocess.Popen(
                [sys.executable, 'auth_server.py'],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen([sys.executable, 'auth_server.py'])

        time.sleep(3)

        if process.poll() is None:
            print(f"✅ Auth server started (PID: {process.pid})")
            return process
        else:
            print("❌ Auth server failed to start")
            return None

    except Exception as e:
        print(f"❌ Error starting auth server: {e}")
        return None


def start_websocket_server():
    try:
        print("🔄 Starting WebSocket server...")

        if platform.system() == "Windows":
            process = subprocess.Popen(
                [sys.executable, 'websocket_server.py'],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen([sys.executable, 'websocket_server.py'])

        time.sleep(2)

        if process.poll() is None:
            print(f"✅ WebSocket server started (PID: {process.pid})")
            return process
        else:
            print("❌ WebSocket server failed to start")
            return None

    except Exception as e:
        print(f"❌ Error starting WebSocket server: {e}")
        return None


def start_game_client():
    try:
        print("🎮 Starting game client...")
        import game_client
        client = game_client.GameClient()
        client.run()
        return True
    except Exception as e:
        print(f"❌ Error starting game client: {e}")
        return False


def check_server_status():
    import requests

    try:
        response = requests.get("http://localhost:8000/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Auth server: Active ({data.get('total_users', 0)} users)")
        else:
            print("❌ Auth server: Error")
    except Exception:
        print("❌ Auth server: Offline")

    try:
        import websockets
        import asyncio

        async def check_ws():
            try:
                uri = "ws://localhost:8765"
                async with websockets.connect(uri, open_timeout=5) as ws:
                    await ws.send('{"type": "ping"}')
                    return True
            except:
                return False

        if asyncio.run(check_ws()):
            print("✅ WebSocket server: Active")
        else:
            print("❌ WebSocket server: Offline")
    except Exception:
        print("❌ WebSocket server: Error")


def show_menu():
    print("\n" + "=" * 50)
    print("🐍 Snake & Ladder Game")
    print("=" * 50)
    print()
    print("Choose option:")
    print("1. 🚀 Start complete game (servers + client)")
    print("2. 🎮 Start game client only")
    print("3. 🔐 Start auth server only")
    print("4. 📡 Start WebSocket server only")
    print("5. 🔍 Check server status")
    print("6. ❌ Exit")
    print()

    while True:
        try:
            choice = input("Enter choice (1-6): ").strip()

            if choice == "1":
                print("\n🚀 Starting complete game...")

                auth_proc = start_auth_server()
                if not auth_proc:
                    print("Failed to start auth server")
                    continue

                ws_proc = start_websocket_server()
                if not ws_proc:
                    print("Failed to start WebSocket server")
                    if auth_proc:
                        auth_proc.terminate()
                    continue

                try:
                    print("\n⏳ Waiting for servers to stabilize...")
                    time.sleep(5)
                    start_game_client()
                finally:
                    print("\n🛑 Shutting down servers...")
                    if auth_proc:
                        auth_proc.terminate()
                    if ws_proc:
                        ws_proc.terminate()
                break

            elif choice == "2":
                print("\n🎮 Starting game client...")
                start_game_client()
                break

            elif choice == "3":
                print("\n🔐 Starting auth server...")
                try:
                    import auth_server
                    import uvicorn
                    uvicorn.run(auth_server.app, host="127.0.0.1", port=8000)
                except KeyboardInterrupt:
                    print("\n🛑 Auth server stopped")
                break

            elif choice == "4":
                print("\n📡 Starting WebSocket server...")
                try:
                    import asyncio
                    from websocket_server import start_server

                    asyncio.run(start_server())
                except KeyboardInterrupt:
                    print("\n🛑 WebSocket server stopped")
                except Exception as e:
                    print(f"❌ Error starting WebSocket server: {e}")
                break

            elif choice == "5":
                print("\n🔍 Checking server status...")
                check_server_status()
                input("\nPress Enter to continue...")

            elif choice == "6":
                print("👋 Goodbye!")
                break

            else:
                print("❌ Invalid choice. Enter 1-6.")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    print("🔍 Snake & Ladder Game Launcher")
    print(f"OS: {platform.system()} {platform.release()}")

    if not check_python_version():
        return

    print("\n📁 Checking required files...")
    if not check_required_files():
        print("\n💡 Make sure all required files are present")
        return

    print("\n📦 Checking dependencies...")
    if not check_and_install_dependencies():
        return

    print("\n✅ All requirements met!")

    show_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("💡 Check that all files are properly installed")