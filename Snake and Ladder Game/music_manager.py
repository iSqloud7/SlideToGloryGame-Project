# music_manager.py - Music system for Snake & Ladder Game

import os
import threading
import time
import random
from typing import Optional, List
import json

# Try to import pygame for Music (most reliable option)
try:
    import pygame

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("pygame not available - Music functionality will be limited")

# Try to import playsound as fallback
try:
    from playsound import playsound

    PLAYSOUND_AVAILABLE = True
except ImportError:
    PLAYSOUND_AVAILABLE = False

# Try to import winsound for Windows
try:
    import winsound

    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


class MusicManager:
    """Manages background Music and sound effects for the game"""

    def __init__(self):
        self.current_track: Optional[str] = None
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.7
        self.music_enabled = True
        self.sound_effects_enabled = True

        # Music library
        self.music_tracks = []
        self.current_track_index = 0
        self.repeat_mode = "playlist"  # "single", "playlist", "off"
        self.shuffle_mode = False

        # Threading
        self.music_thread = None
        self.stop_music_flag = threading.Event()

        # Initialize audio system
        self.audio_system = self._initialize_audio_system()

        # Load settings
        self.load_settings()

        # Scan for Music files
        self.scan_music_directory()

    def _initialize_audio_system(self) -> str:
        """Initialize the best available audio system"""
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.init()
                return "pygame"
            except:
                pass

        if PLAYSOUND_AVAILABLE:
            return "playsound"

        if WINSOUND_AVAILABLE:
            return "winsound"

        return "none"

    def scan_music_directory(self, directory: str = "Music"):
        """Scan for Music files in the specified directory"""
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            self._create_readme_file(directory)
            return

        supported_formats = ['.mp3', '.wav', '.ogg']
        if self.audio_system == "pygame":
            supported_formats.extend(['.midi', '.mod', '.xm', '.it', '.s3m'])

        self.music_tracks = []
        for file in os.listdir(directory):
            if any(file.lower().endswith(ext) for ext in supported_formats):
                self.music_tracks.append(os.path.join(directory, file))

        self.music_tracks.sort()  # Sort alphabetically

        if self.music_tracks:
            print(f"Found {len(self.music_tracks)} Music tracks")
        else:
            print("No Music files found. Add .mp3, .wav, or .ogg files to the 'Music' directory")

    def _create_readme_file(self, directory: str):
        """Create a README file in the Music directory"""
        readme_content = """Snake & Ladder Game - Music Directory

Place your Music files here to add background Music to the game!

Supported formats:
- .mp3 (recommended)
- .wav
- .ogg
- .midi (if pygame is available)

The game will automatically detect and play these files.
You can control Music playback from the game's Music controls.

Tips:
- Keep file sizes reasonable for smooth gameplay
- Instrumental or ambient Music works best for background
- The game supports playlist mode and shuffle
"""

        try:
            with open(os.path.join(directory, "README.txt"), "w") as f:
                f.write(readme_content)
        except:
            pass

    def load_settings(self):
        """Load Music settings from file"""
        try:
            if os.path.exists("music_settings.json"):
                with open("music_settings.json", "r") as f:
                    settings = json.load(f)
                    self.volume = settings.get("volume", 0.7)
                    self.music_enabled = settings.get("music_enabled", True)
                    self.sound_effects_enabled = settings.get("sound_effects_enabled", True)
                    self.repeat_mode = settings.get("repeat_mode", "playlist")
                    self.shuffle_mode = settings.get("shuffle_mode", False)
        except Exception as e:
            print(f"Error loading Music settings: {e}")

    def save_settings(self):
        """Save Music settings to file"""
        try:
            settings = {
                "volume": self.volume,
                "music_enabled": self.music_enabled,
                "sound_effects_enabled": self.sound_effects_enabled,
                "repeat_mode": self.repeat_mode,
                "shuffle_mode": self.shuffle_mode
            }
            with open("music_settings.json", "w") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving Music settings: {e}")

    def play_music(self, track: Optional[str] = None):
        """Start playing Music"""
        if not self.music_enabled or not self.music_tracks:
            return False

        if track:
            if track in self.music_tracks:
                self.current_track_index = self.music_tracks.index(track)
            else:
                return False
        elif self.shuffle_mode and not self.current_track:
            self.current_track_index = random.randint(0, len(self.music_tracks) - 1)

        self.current_track = self.music_tracks[self.current_track_index]

        if self.music_thread and self.music_thread.is_alive():
            self.stop_music()

        self.stop_music_flag.clear()
        self.music_thread = threading.Thread(target=self._music_player_thread, daemon=True)
        self.music_thread.start()

        return True

    def _music_player_thread(self):
        """Background thread for Music playback"""
        while not self.stop_music_flag.is_set():
            if not self.current_track or not os.path.exists(self.current_track):
                break

            try:
                self.is_playing = True
                self.is_paused = False

                if self.audio_system == "pygame":
                    self._play_with_pygame()
                elif self.audio_system == "playsound":
                    self._play_with_playsound()
                elif self.audio_system == "winsound":
                    self._play_with_winsound()

                # Handle track completion
                if not self.stop_music_flag.is_set():
                    self._handle_track_end()

            except Exception as e:
                print(f"Error playing Music: {e}")
                break

        self.is_playing = False
        self.is_paused = False

    def _play_with_pygame(self):
        """Play Music using pygame"""
        try:
            pygame.mixer.music.load(self.current_track)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()

            # Wait for Music to finish or stop signal
            while pygame.mixer.music.get_busy() and not self.stop_music_flag.is_set():
                if self.is_paused:
                    pygame.mixer.music.pause()
                    while self.is_paused and not self.stop_music_flag.is_set():
                        time.sleep(0.1)
                    if not self.stop_music_flag.is_set():
                        pygame.mixer.music.unpause()

                time.sleep(0.1)

        except Exception as e:
            print(f"Pygame Music error: {e}")

    def _play_with_playsound(self):
        """Play Music using playsound (blocking)"""
        try:
            # playsound is blocking, so we can't easily implement pause/resume
            playsound(self.current_track, block=True)
        except Exception as e:
            print(f"Playsound error: {e}")

    def _play_with_winsound(self):
        """Play Music using winsound (Windows only, limited formats)"""
        try:
            if self.current_track.lower().endswith('.wav'):
                winsound.PlaySound(self.current_track,
                                   winsound.SND_FILENAME | winsound.SND_ASYNC)

                # Simple wait loop (can't detect when finished)
                time.sleep(30)  # Assume 30 second tracks for demo
        except Exception as e:
            print(f"Winsound error: {e}")

    def _handle_track_end(self):
        """Handle what happens when a track ends"""
        if self.repeat_mode == "single":
            # Play the same track again
            pass
        elif self.repeat_mode == "playlist":
            # Move to next track
            self._next_track()
        else:  # "off"
            self.stop_music()
            return

    def _next_track(self):
        """Move to the next track"""
        if not self.music_tracks:
            return

        if self.shuffle_mode:
            self.current_track_index = random.randint(0, len(self.music_tracks) - 1)
        else:
            self.current_track_index = (self.current_track_index + 1) % len(self.music_tracks)

        self.current_track = self.music_tracks[self.current_track_index]

    def pause_music(self):
        """Pause the currently playing Music"""
        if not self.is_playing or self.is_paused:
            return False

        self.is_paused = True

        if self.audio_system == "pygame":
            try:
                pygame.mixer.music.pause()
                return True
            except:
                pass

        return False

    def resume_music(self):
        """Resume paused Music"""
        if not self.is_playing or not self.is_paused:
            return False

        self.is_paused = False

        if self.audio_system == "pygame":
            try:
                pygame.mixer.music.unpause()
                return True
            except:
                pass

        return False

    def stop_music(self):
        """Stop the currently playing Music"""
        self.stop_music_flag.set()

        if self.audio_system == "pygame":
            try:
                pygame.mixer.music.stop()
            except:
                pass

        self.is_playing = False
        self.is_paused = False
        self.current_track = None

        if self.music_thread:
            self.music_thread.join(timeout=1)

    def next_track(self):
        """Skip to the next track"""
        if not self.music_tracks:
            return False

        self.stop_music()
        self._next_track()
        return self.play_music()

    def previous_track(self):
        """Go to the previous track"""
        if not self.music_tracks:
            return False

        self.stop_music()

        if self.shuffle_mode:
            self.current_track_index = random.randint(0, len(self.music_tracks) - 1)
        else:
            self.current_track_index = (self.current_track_index - 1) % len(self.music_tracks)

        self.current_track = self.music_tracks[self.current_track_index]
        return self.play_music()

    def set_volume(self, volume: float):
        """Set the Music volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))

        if self.audio_system == "pygame" and self.is_playing:
            try:
                pygame.mixer.music.set_volume(self.volume)
            except:
                pass

        self.save_settings()

    def toggle_music(self):
        """Toggle Music on/off"""
        self.music_enabled = not self.music_enabled
        if not self.music_enabled:
            self.stop_music()
        self.save_settings()
        return self.music_enabled

    def toggle_sound_effects(self):
        """Toggle sound effects on/off"""
        self.sound_effects_enabled = not self.sound_effects_enabled
        self.save_settings()
        return self.sound_effects_enabled

    def play_sound_effect(self, sound_file: str):
        """Play a sound effect"""
        if not self.sound_effects_enabled:
            return False

        if not os.path.exists(sound_file):
            return False

        try:
            if self.audio_system == "pygame":
                sound = pygame.mixer.Sound(sound_file)
                sound.set_volume(self.volume)
                sound.play()
                return True
        except Exception as e:
            print(f"Error playing sound effect: {e}")

        return False

    def get_current_track_info(self) -> dict:
        """Get information about the currently playing track"""
        if not self.current_track:
            return {"title": "No track", "status": "stopped"}

        track_name = os.path.basename(self.current_track)
        track_name = os.path.splitext(track_name)[0]  # Remove extension

        status = "playing" if self.is_playing and not self.is_paused else \
            "paused" if self.is_paused else "stopped"

        return {
            "title": track_name,
            "status": status,
            "track_number": self.current_track_index + 1,
            "total_tracks": len(self.music_tracks),
            "volume": int(self.volume * 100),
            "repeat_mode": self.repeat_mode,
            "shuffle_mode": self.shuffle_mode
        }

    def get_playlist(self) -> List[str]:
        """Get the list of available tracks"""
        return [os.path.splitext(os.path.basename(track))[0] for track in self.music_tracks]

    def cleanup(self):
        """Clean up resources"""
        self.stop_music()
        if self.audio_system == "pygame":
            try:
                pygame.mixer.quit()
            except:
                pass


# Convenience functions for easy integration
music_manager = None


def initialize_music():
    """Initialize the global Music manager"""
    global music_manager
    if music_manager is None:
        music_manager = MusicManager()
    return music_manager


def play_background_music():
    """Start playing background Music"""
    manager = initialize_music()
    return manager.play_music()


def pause_music():
    """Pause background Music"""
    if music_manager:
        return music_manager.pause_music()
    return False


def resume_music():
    """Resume background Music"""
    if music_manager:
        return music_manager.resume_music()
    return False


def stop_music():
    """Stop background Music"""
    if music_manager:
        music_manager.stop_music()


def toggle_music():
    """Toggle Music on/off"""
    manager = initialize_music()
    return manager.toggle_music()


def set_volume(volume: float):
    """Set Music volume"""
    manager = initialize_music()
    manager.set_volume(volume)


def get_music_info():
    """Get current Music information"""
    if music_manager:
        return music_manager.get_current_track_info()
    return {"title": "Music not initialized", "status": "stopped"}


if __name__ == "__main__":
    # Test the Music manager
    print("Testing Music Manager...")

    manager = MusicManager()
    print(f"Audio system: {manager.audio_system}")
    print(f"Music tracks found: {len(manager.music_tracks)}")

    if manager.music_tracks:
        print("Starting Music...")
        manager.play_music()

        time.sleep(3)
        print("Pausing...")
        manager.pause_music()

        time.sleep(2)
        print("Resuming...")
        manager.resume_music()

        time.sleep(3)
        print("Stopping...")
        manager.stop_music()

    manager.cleanup()
    print("Test completed!")