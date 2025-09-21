from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import hashlib
import datetime
import os

app = FastAPI(title="Snake & Ladder Auth Server", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

USERS_FILE = "users.json"


class UserCredentials(BaseModel):
    username: str
    password: str


class UpdateStatsRequest(BaseModel):
    username: str
    user_data: dict


def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading users: {e}")
    return {}


def save_users(users):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving users: {e}")
        return False


def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def validate_credentials(username, password):
    username = username.strip()
    password = password.strip()

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(password) < 4:
        return False, "Password must be at least 4 characters"

    invalid_chars = ['<', '>', '"', "'", '&', '/', '\\']
    for char in invalid_chars:
        if char in username or char in password:
            return False, "Invalid characters in credentials"

    return True, "Valid"


@app.get("/")
async def root():
    return {
        "name": "Snake & Ladder Auth Server",
        "version": "2.0",
        "endpoints": ["/register", "/login", "/status", "/update_stats", "/leaderboard"],
        "users": len(load_users()),
        "status": "active"
    }


@app.post("/register")
async def register(credentials: UserCredentials):
    valid, msg = validate_credentials(credentials.username, credentials.password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    users = load_users()

    username_lower = credentials.username.lower()
    for existing_user in users.keys():
        if existing_user.lower() == username_lower:
            raise HTTPException(status_code=400, detail="Username already exists")

    users[credentials.username] = {
        "password_hash": hash_password(credentials.password),
        "created_at": datetime.datetime.now().isoformat(),
        "last_login": None,
        "stats": {
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "fastest_win": None,
            "longest_game": None,
            "win_streak": 0,
            "best_win_streak": 0,
            "total_playtime": 0,
            "last_played": None
        }
    }

    if save_users(users):
        return {
            "success": True,
            "message": "User registered successfully",
            "username": credentials.username
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to save user data")


@app.post("/login")
async def login(credentials: UserCredentials):
    users = load_users()

    user_key = None
    username_lower = credentials.username.lower()
    for key in users.keys():
        if key.lower() == username_lower:
            user_key = key
            break

    if not user_key:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_data = users[user_key]
    password_hash = hash_password(credentials.password)

    if user_data["password_hash"] != password_hash:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_data["last_login"] = datetime.datetime.now().isoformat()
    users[user_key] = user_data
    save_users(users)

    return {
        "success": True,
        "message": "Login successful",
        "username": user_key,
        "user_data": user_data.get("stats", {})
    }


@app.post("/update_stats")
async def update_stats(request: UpdateStatsRequest):
    """Update user statistics"""
    try:
        username = request.username
        user_data = request.user_data

        if not username:
            raise HTTPException(status_code=400, detail="Username required")

        users = load_users()

        # Find user (case-insensitive)
        user_key = None
        username_lower = username.lower()
        for key in users.keys():
            if key.lower() == username_lower:
                user_key = key
                break

        if not user_key:
            raise HTTPException(status_code=404, detail="User not found")

        # Update user stats - merge with existing stats
        current_stats = users[user_key].get("stats", {})

        # Take the maximum values for cumulative stats
        updated_stats = {
            "games_played": max(current_stats.get("games_played", 0), user_data.get("games_played", 0)),
            "wins": max(current_stats.get("wins", 0), user_data.get("wins", 0)),
            "losses": max(current_stats.get("losses", 0), user_data.get("losses", 0))
        }

        # For fastest_win, take the better (lower) time if both exist
        current_fastest = current_stats.get("fastest_win")
        new_fastest = user_data.get("fastest_win")

        if current_fastest is not None and new_fastest is not None:
            updated_stats["fastest_win"] = min(current_fastest, new_fastest)
        elif new_fastest is not None:
            updated_stats["fastest_win"] = new_fastest
        elif current_fastest is not None:
            updated_stats["fastest_win"] = current_fastest
        else:
            updated_stats["fastest_win"] = None

        # Update additional stats if provided
        for stat_key in ["longest_game", "win_streak", "best_win_streak", "total_playtime"]:
            if stat_key in user_data:
                if stat_key in ["best_win_streak", "longest_game", "total_playtime"]:
                    # Take maximum for these cumulative/best stats
                    updated_stats[stat_key] = max(
                        current_stats.get(stat_key, 0) or 0,
                        user_data[stat_key] or 0
                    )
                else:
                    # Direct update for current stats like win_streak
                    updated_stats[stat_key] = user_data[stat_key]

        # Update last_played if provided
        if "last_played" in user_data:
            updated_stats["last_played"] = user_data["last_played"]

        users[user_key]["stats"] = updated_stats

        if save_users(users):
            return {
                "success": True,
                "message": "Statistics updated successfully",
                "updated_stats": updated_stats
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save user data")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/user_stats/{username}")
async def get_user_stats(username: str):
    """Get detailed statistics for a specific user"""
    users = load_users()

    # Find user (case-insensitive)
    user_key = None
    username_lower = username.lower()
    for key in users.keys():
        if key.lower() == username_lower:
            user_key = key
            break

    if not user_key:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = users[user_key]
    stats = user_data.get("stats", {})

    return {
        "username": user_key,
        "created_at": user_data.get("created_at"),
        "last_login": user_data.get("last_login"),
        "stats": stats
    }


@app.get("/leaderboard")
async def get_leaderboard():
    """Get leaderboard of top players"""
    users = load_users()

    leaderboard_data = []
    for username, user_data in users.items():
        stats = user_data.get("stats", {})
        games_played = stats.get("games_played", 0)
        wins = stats.get("wins", 0)

        if games_played > 0:  # Only include users who have played games
            win_rate = round((wins / games_played) * 100, 1)
            leaderboard_data.append({
                "username": username,
                "games_played": games_played,
                "wins": wins,
                "losses": stats.get("losses", 0),
                "win_rate": win_rate,
                "fastest_win": stats.get("fastest_win"),
                "best_win_streak": stats.get("best_win_streak", 0),
                "last_played": stats.get("last_played")
            })

    # Sort by wins, then by win rate, then by games played
    leaderboard_data.sort(key=lambda x: (x["wins"], x["win_rate"], x["games_played"]), reverse=True)

    return {
        "leaderboard": leaderboard_data[:50],  # Top 50 players
        "total_players": len(leaderboard_data)
    }


@app.get("/status")
async def status():
    users = load_users()
    return {
        "server": "active",
        "total_users": len(users),
        "timestamp": datetime.datetime.now().isoformat(),
        "storage": "JSON file",
        "file_exists": os.path.exists(USERS_FILE)
    }


@app.get("/users")
async def list_users():
    users = load_users()
    user_list = []

    for username, data in users.items():
        user_list.append({
            "username": username,
            "created_at": data.get("created_at"),
            "last_login": data.get("last_login"),
            "stats": data.get("stats", {})
        })

    return {"users": user_list}


if __name__ == "__main__":
    print("Starting Snake & Ladder Auth Server...")
    print("URL: http://localhost:8000")
    print("Status: http://localhost:8000/status")
    print("Press Ctrl+C to stop")

    if not os.path.exists(USERS_FILE):
        save_users({})
        print(f"Created {USERS_FILE}")

    import uvicorn

    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except KeyboardInterrupt:
        print("\nAuth server stopped")