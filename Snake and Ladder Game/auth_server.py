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
        "endpoints": ["/register", "/login", "/status"],
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
            "losses": 0
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