import sqlite3
import hashlib
import secrets
from typing import Optional

DB_PATH = "data/f1.sqlite"


class AuthService:
    """Handles user registration, login, and favorite driver management."""

    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._ensure_password_column()

    def _connect(self) -> sqlite3.Connection:
        """Opens a database connection."""
        return sqlite3.connect(self._db_path)

    def _ensure_password_column(self):
        """Adds password_hash column to users table if missing."""
        conn = self._connect()
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "password_hash" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            conn.commit()
        conn.close()

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hashes a password with a random salt using SHA-256."""
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}${h}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        """Verifies a password against a stored salt$hash."""
        if not stored_hash or "$" not in stored_hash:
            return False
        salt, h = stored_hash.split("$", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h

    def register(self, name: str, password: str, favorite_driver: Optional[str] = None) -> tuple[bool, str]:
        """Registers a new user. Returns (success, message)."""
        conn = self._connect()
        existing = conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
        if existing:
            conn.close()
            return False, "Username already exists."
        pw_hash = self._hash_password(password)
        conn.execute(
            "INSERT INTO users (name, password_hash, favorite_driver, created_at, updated_at) "
            "VALUES (?, ?, ?, datetime('now'), datetime('now'))",
            (name, pw_hash, favorite_driver),
        )
        conn.commit()
        conn.close()
        return True, "Registration successful."

    def login(self, name: str, password: str) -> tuple[bool, str, Optional[dict]]:
        """Authenticates a user. Returns (success, message, user_dict_or_None)."""
        conn = self._connect()
        row = conn.execute(
            "SELECT id, name, password_hash, favorite_driver FROM users WHERE name = ?",
            (name,),
        ).fetchone()
        if not row:
            conn.close()
            return False, "User not found.", None
        uid, uname, pw_hash, fav = row
        if not pw_hash:
            conn.close()
            return False, "Account has no password. Please register again.", None
        if not self._verify_password(password, pw_hash):
            conn.close()
            return False, "Wrong password.", None
        conn.execute(
            "INSERT INTO login_events (user_id, login_at) VALUES (?, datetime('now'))",
            (uid,),
        )
        conn.commit()
        conn.close()
        return True, "Login successful.", {"id": uid, "name": uname, "favorite_driver": fav}

    def update_favorite_driver(self, user_id: int, driver_code: str):
        """Updates the favorite driver for a user."""
        conn = self._connect()
        conn.execute(
            "UPDATE users SET favorite_driver = ?, updated_at = datetime('now') WHERE id = ?",
            (driver_code, user_id),
        )
        conn.commit()
        conn.close()

    def get_popular_drivers(self, limit: int = 5) -> list[str]:
        """Returns the most popular favorite drivers across all users."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT favorite_driver, COUNT(*) as cnt FROM users "
            "WHERE favorite_driver IS NOT NULL "
            "GROUP BY favorite_driver ORDER BY cnt DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]

    def get_all_driver_codes(self) -> list[str]:
        """Returns all known driver codes from the driver_directory table."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT driver_code FROM driver_directory ORDER BY driver_code"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
