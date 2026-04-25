from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

from src.database.base_repository import BaseRepository


class UserRepository(BaseRepository):
    """
    Handles all user-related database operations.

    Responsibilities:
    - Create user (register)
    - Find user by name
    - Verify password
    - Update favorite driver
    - Log login events

    Pattern: Repository
    """

    def ensure_schema(self) -> None:
        """Creates users and login_events tables if missing, adds password_hash column if needed."""
        with self._connect() as conn:
            # Create users table if it doesn't exist
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    favorite_driver TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # Create login_events table if it doesn't exist
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS login_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
                """
            )
            
            # Add password_hash column if missing (for existing databases)
            cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "password_hash" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

    def find_by_name(self, name: str) -> Optional[dict]:
        """Returns a user dict or None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, password_hash, favorite_driver FROM users WHERE name = ?",
                (name,),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def exists(self, name: str) -> bool:
        """Returns True if a user with this name already exists."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE name = ?", (name,)
            ).fetchone()
        return row is not None

    def create(self, name: str, password_hash: str, favorite_driver: Optional[str]) -> int:
        """Inserts a new user and returns the new user id."""
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, password_hash, favorite_driver, created_at, updated_at) "
                "VALUES (?, ?, ?, datetime('now'), datetime('now'))",
                (name, password_hash, favorite_driver),
            )
            return cursor.lastrowid

    def update_favorite_driver(self, user_id: int, driver_code: str) -> None:
        """Updates the favorite driver for a user."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET favorite_driver = ?, updated_at = datetime('now') WHERE id = ?",
                (driver_code, user_id),
            )

    def log_login(self, user_id: int) -> None:
        """Records a login event."""
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO login_events (user_id, login_at) VALUES (?, datetime('now'))",
                (user_id,),
            )

    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes a password using Argon2id (includes salt and parameters in the output)."""
        ph = PasswordHasher()
        return ph.hash(password)

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Returns True if the password matches the Argon2id hash."""
        if not stored_hash:
            return False
        ph = PasswordHasher()
        try:
            return ph.verify(stored_hash, password)
        except (VerifyMismatchError, InvalidHash):
            return False
