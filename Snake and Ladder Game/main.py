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

    # Music-related packages (optional but recommended)
    music_packages = {
        'pygame': 'pygame>=2.0.0'
    }

    missing_packages = []
    missing_music = []

    # Check required packages
    for package, pip_name in required_packages.items():
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - missing")
            missing_packages.append(pip_name)

    # Check Music packages
    for package, pip_name in music_packages.items():
        try:
            importlib.import_module(package)
            print(f"✅ {package} (Music support)")
        except ImportError:
            print(f"⚠️  {package} - missing (recommended for Music)")
            missing_music.append(pip_name)

    # Install required packages
    if missing_packages:
        print(f"\n📦 Installing required: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                                      sys.executable, "-m", "pip", "install"
                                  ] + missing_packages)
            print("✅ Required packages installed!")
        except subprocess.CalledProcessError:
            print("❌ Installation failed. Try manually:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False

    # Offer to install Music packages
    if missing_music:
        print(f"\n🎵 Optional Music packages available: {', '.join(missing_music)}")
        response = input("Install Music support packages? (y/n): ").lower().strip()
        if response == 'y':
            try:
                subprocess.check_call([
                                          sys.executable, "-m", "pip", "install"
                                      ] + missing_music)
                print("✅ Music packages installed!")
            except subprocess.CalledProcessError:
                print("⚠️  Music package installation failed, but game will still work")

    return True


def check_required_files():
    required_files = [
        'auth_server.py',
        'websocket_server.py',
        'game_client.py',
        'snake_ladder_core.py',
        'utils.py'
    ]

    optional_files = [
        'music_manager.py',
        'stats.py'
    ]

    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            missing.append(file)
            print(f"❌ {file} - missing")

    for file in optional_files:
        if os.path.exists(file):
            print(f"✅ {file} (optional)")
        else:
            print(f"⚠️  {file} - missing (optional)")

    if missing:
        print(f"\n❌ Missing required files: {', '.join(missing)}")
        return False

    return True


def setup_music_directory():
    """Create Music directory and add sample info"""
    music_dir = "Music"
    if not os.path.exists(music_dir):
        os.makedirs(music_dir)
        print(f"📁 Created Music directory: {music_dir}")

        # Create info file
        info_content = """🎵 Snake & Ladder Game - Music Setup

Add your Music files to this directory for background Music!

Supported formats:
- .mp3 (recommended)
- .wav 
- .ogg
- .midi (if pygame is installed)

Instructions:
1. Copy your Music files to this 'Music' directory
2. Start the game - Music will automatically load
3. Use the Music controls in the main menu

Tips:
- Instrumental or ambient Music works best
- Keep file sizes reasonable (under 10MB each)
- The game supports playlist mode and shuffle

Sample free Music sources:
- Freesound.org (CC licensed)
- Incompetech.com (royalty-free)
- Bensound.com (free tracks available)

Enjoy your musical Snake & Ladder experience!
"""
        try:
            with open(os.path.join(music_dir, "README.txt"), "w", encoding="utf-8") as f:
                f.write(info_content)
        except:
            pass
    else:
        music_files = [f for f in os.listdir(music_dir)
                       if f.lower().endswith(('.mp3', '.wav', '.ogg', '.midi'))]
        if music_files:
            print(f"🎵 Found {len(music_files)} Music files")
        else:
            print(f"📁 Music directory exists but is empty")


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
        print("🎮 Starting game client with Music support...")

        # Try to import Music manager to verify it's available
        try:
            import music_manager
            print("🎵 Music system available")
        except ImportError:
            print("⚠️  Music system not available (music_manager.py missing)")

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
    print("\n" + "=" * 60)
    print("🐍🎵 Snake & Ladder Game with Music Support")
    print("=" * 60)
    print()
    print("Choose option:")
    print("1. 🚀 Start complete game (servers + client)")
    print("2. 🎮 Start game client only")
    print("3. 🔐 Start auth server only")
    print("4. 📡 Start WebSocket server only")
    print("5. 🔍 Check server status")
    print("6. 🎵 Setup Music directory")
    print("7. 📋 Show Music info")
    print("8. ❌ Exit")
    print()

    while True:
        try:
            choice = input("Enter choice (1-8): ").strip()

            if choice == "1":
                print("\n🚀 Starting complete game with Music...")

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
                print("\n🎵 Setting up Music directory...")
                setup_music_directory()
                input("\nPress Enter to continue...")

            elif choice == "7":
                print("\n📋 Music System Information:")
                show_music_info()
                input("\nPress Enter to continue...")

            elif choice == "8":
                print("👋 Goodbye!")
                break

            else:
                print("❌ Invalid choice. Enter 1-8.")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def show_music_info():
    """Display information about the Music system"""
    print("\n🎵 Music System Status:")
    print("-" * 40)

    # Check if Music manager exists
    if os.path.exists("music_manager.py"):
        print("✅ Music manager: Available")
    else:
        print("❌ Music manager: Missing (music_manager.py not found)")
        return

    # Check audio libraries
    audio_libs = []

    try:
        import pygame
        audio_libs.append("pygame (recommended)")
        print("✅ Pygame: Available (best audio support)")
    except ImportError:
        print("⚠️  Pygame: Not installed")
        print("   Install with: pip install pygame")

    try:
        from playsound import playsound
        audio_libs.append("playsound")
        print("✅ Playsound: Available")
    except ImportError:
        print("⚠️  Playsound: Not installed")

    try:
        import winsound
        audio_libs.append("winsound (Windows only)")
        print("✅ Winsound: Available (Windows)")
    except ImportError:
        if platform.system() == "Windows":
            print("⚠️  Winsound: Not available")

    if not audio_libs:
        print("❌ No audio libraries available!")
        print("   Install pygame for best experience: pip install pygame")
        return

    # Check Music directory
    music_dir = "Music"
    if os.path.exists(music_dir):
        music_files = [f for f in os.listdir(music_dir)
                       if f.lower().endswith(('.mp3', '.wav', '.ogg', '.midi', '.mod'))]
        if music_files:
            print(f"✅ Music files: {len(music_files)} found")
            print("   Formats found:", set(os.path.splitext(f)[1].lower() for f in music_files))
        else:
            print("⚠️  Music directory is empty")
            print("   Add .mp3, .wav, or .ogg files to enable Music")
    else:
        print("⚠️  Music directory doesn't exist")
        print("   Run option 6 to create it")

    print("\n🎵 Supported Features:")
    print("- Background Music playback")
    print("- Play/pause/stop controls")
    print("- Volume adjustment")
    print("- Next/previous track")
    print("- Playlist view")
    print("- Shuffle and repeat modes")

    if "pygame" in str(audio_libs):
        print("- Advanced audio features (with pygame)")


def main():
    print("🔍 Snake & Ladder Game Launcher with Music")
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

    print("\n🎵 Checking Music setup...")
    setup_music_directory()

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