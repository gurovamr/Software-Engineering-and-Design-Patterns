import hashlib
import secrets
from typing import Optional

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
        """Adds password_hash column if missing (safe migration)."""
        with self._connect() as conn:
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
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO login_events (user_id, login_at) VALUES (?, datetime('now'))",
                (user_id,),
            )

    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes a password with a random salt using SHA-256."""
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}${h}"

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """Returns True if the password matches the stored salt$hash."""
        if not stored_hash or "$" not in stored_hash:
            return False
        salt, h = stored_hash.split("$", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
