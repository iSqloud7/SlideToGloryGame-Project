#!/usr/bin/env python3
"""
Setup script for Snake & Ladder Game Music System
This script will help you quickly set up music functionality
"""

import os
import sys
import subprocess
import urllib.request
import json


def install_pygame():
    """Install pygame for music support"""
    print("Installing pygame for music support...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame>=2.0.0"])
        print("✅ Pygame installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install pygame")
        print("Try manually: pip install pygame")
        return False


def create_music_directory():
    """Create music directory with sample files info"""
    music_dir = "music"
    if not os.path.exists(music_dir):
        os.makedirs(music_dir)
        print(f"📁 Created directory: {music_dir}")
    else:
        print(f"📁 Directory already exists: {music_dir}")

    # Create comprehensive README
    readme_path = os.path.join(music_dir, "README.md")
    readme_content = """# 🎵 Music Setup for Snake & Ladder Game

## Quick Start
1. Add your music files to this directory
2. Supported formats: `.mp3`, `.wav`, `.ogg`, `.midi`
3. Start the game and enjoy background music!

## Recommended Music Types
- **Instrumental tracks** - Won't distract from gameplay
- **Ambient music** - Creates a relaxing atmosphere
- **Game soundtracks** - Fits the gaming mood
- **Classical or acoustic** - Timeless and pleasant

## File Size Recommendations
- Keep files under 10MB each for smooth loading
- 3-5 minute tracks work well for game sessions
- Consider using compressed formats like MP3

## Free Music Sources
- **Freesound.org** - Creative Commons licensed sounds
- **Incompetech.com** - Royalty-free music by Kevin MacLeod
- **Bensound.com** - Free tracks available
- **OpenGameArt.org** - Game-specific music
- **YouTube Audio Library** - Free music for projects

## Music Controls in Game
- **Play/Pause** - Start or pause background music
- **Stop** - Stop music completely
- **Next/Previous** - Skip between tracks
- **Volume** - Adjust music volume (0-100%)
- **Playlist** - View and select specific tracks
- **Shuffle** - Random track order
- **Repeat** - Loop single track or entire playlist

## Troubleshooting
- **No music plays**: Check if pygame is installed (`pip install pygame`)
- **Unsupported format**: Convert to MP3, WAV, or OGG
- **Music too loud**: Use the in-game volume control
- **Game lag**: Try smaller audio files or lower quality

## Technical Notes
- The game uses pygame for audio (best support)
- Falls back to playsound or winsound if pygame unavailable
- Music runs in background thread for smooth gameplay
- Settings are saved between game sessions

Enjoy your musical Snake & Ladder experience! 🎮🎵
"""

    try:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        print(f"📄 Created README: {readme_path}")
    except Exception as e:
        print(f"Warning: Could not create README - {e}")


def download_sample_music():
    """Offer to download a sample music track"""
    print("\n🎵 Would you like to download a sample music track?")
    print("This will download a short, free Creative Commons track for testing.")

    choice = input("Download sample track? (y/n): ").lower().strip()
    if choice != 'y':
        return

    # Sample free music URL (you'd replace this with an actual CC track)
    sample_url = "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"  # Example
    sample_file = "music/sample_track.wav"

    print("📥 This would download a sample track in a real implementation...")
    print("For now, please add your own music files to the 'music' directory.")


def check_music_files():
    """Check for existing music files"""
    music_dir = "music"
    if not os.path.exists(music_dir):
        return []

    supported_extensions = {'.mp3', '.wav', '.ogg', '.midi', '.mid', '.mod', '.xm', '.it', '.s3m'}
    music_files = []

    for file in os.listdir(music_dir):
        if any(file.lower().endswith(ext) for ext in supported_extensions):
            music_files.append(file)

    return sorted(music_files)


def create_sample_playlist():
    """Create a sample playlist configuration"""
    playlist_config = {
        "default_volume": 0.7,
        "auto_start": True,
        "repeat_mode": "playlist",  # "single", "playlist", "off"
        "shuffle_mode": False,
        "fade_in": True,
        "fade_out": True
    }

    config_path = "music_config.json"
    try:
        with open(config_path, "w") as f:
            json.dump(playlist_config, f, indent=2)
        print(f"⚙️ Created config file: {config_path}")
    except Exception as e:
        print(f"Warning: Could not create config - {e}")


def test_audio_system():
    """Test if audio system is working"""
    print("\n🔍 Testing audio system...")

    # Test pygame
    try:
        import pygame
        pygame.mixer.pre_init()
        pygame.mixer.init()
        print("✅ Pygame audio: Working")
        pygame.mixer.quit()
        return True
    except Exception as e:
        print(f"❌ Pygame audio: {e}")

    # Test playsound
    try:
        from playsound import playsound
        print("✅ Playsound: Available")
        return True
    except ImportError:
        print("⚠️ Playsound: Not available")

    # Test winsound (Windows)
    if os.name == 'nt':
        try:
            import winsound
            print("✅ Winsound: Available (Windows)")
            return True
        except ImportError:
            print("⚠️ Winsound: Not available")

    print("❌ No audio systems available!")
    return False


def main():
    print("🎵 Snake & Ladder Game - Music Setup")
    print("=" * 50)

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return

    print("✅ Python version OK")

    # Install pygame
    print("\n📦 Setting up audio support...")
    try:
        import pygame
        print("✅ Pygame already installed")
    except ImportError:
        if not install_pygame():
            print("⚠️ Continuing without pygame - limited audio support")

    # Test audio
    audio_ok = test_audio_system()
    if not audio_ok:
        print("⚠️ Audio system issues detected")
        print("Try: pip install pygame playsound")

    # Create music directory
    print("\n📁 Setting up music directory...")
    create_music_directory()

    # Check existing music
    music_files = check_music_files()
    if music_files:
        print(f"\n🎵 Found {len(music_files)} music files:")
        for i, file in enumerate(music_files[:5], 1):  # Show first 5
            print(f"   {i}. {file}")
        if len(music_files) > 5:
            print(f"   ... and {len(music_files) - 5} more")
    else:
        print("\n📭 No music files found")
        print("Add .mp3, .wav, or .ogg files to the 'music' directory")

    # Create config
    print("\n⚙️ Creating configuration...")
    create_sample_playlist()

    # Final instructions
    print("\n" + "=" * 50)
    print("🎉 Music setup complete!")
    print("\nNext steps:")
    print("1. Add your music files to the 'music' directory")
    print("2. Run the main game: python main.py")
    print("3. Use music controls in the main menu")

    if not music_files:
        print("\n💡 Tips:")
        print("- MP3 format is recommended for compatibility")
        print("- Keep files under 10MB for smooth performance")
        print("- Instrumental music works best for gaming")

    if not audio_ok:
        print("\n⚠️ Audio Issues:")
        print("Install pygame for best music support:")
        print("   pip install pygame")

    print("\n🎮 Happy gaming with music! 🎵")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
    except Exception as e:
        print(f"\nSetup error: {e}")