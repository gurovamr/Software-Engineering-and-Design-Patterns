from typing import Optional

from src.database.driver_repository import DriverRepository
from src.database.user_repository import UserRepository

DB_PATH = "data/f1.sqlite"


class AuthService:
    """
    Handles user registration, login, and favorite driver management.

    Pattern: Service Layer
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self._repo = UserRepository(db_path=db_path)
        self._repo.ensure_schema()

    def register(self, name: str, password: str, favorite_driver: Optional[str] = None) -> tuple[bool, str]:
        """Registers a new user. Returns (success, message)."""
        if self._repo.exists(name):
            return False, "Username already exists."
        pw_hash = UserRepository.hash_password(password)
        self._repo.create(name, pw_hash, favorite_driver)
        return True, "Registration successful."

    def login(self, name: str, password: str) -> tuple[bool, str, Optional[dict]]:
        """Authenticates a user. Returns (success, message, user_dict_or_None)."""
        user = self._repo.find_by_name(name)
        if not user:
            return False, "User not found.", None
        if not user.get("password_hash"):
            return False, "Account has no password. Please register again.", None
        if not UserRepository.verify_password(password, user["password_hash"]):
            return False, "Wrong password.", None
        self._repo.log_login(user["id"])
        return True, "Login successful.", {
            "id": user["id"],
            "name": user["name"],
            "favorite_driver": user["favorite_driver"],
        }

    def update_favorite_driver(self, user_id: int, driver_code: str) -> None:
        """Updates the favorite driver for a user."""
        self._repo.update_favorite_driver(user_id, driver_code)


class DriverService:
    """
    Service-Layer wrapper around DriverRepository.

    Responsibilities:
    - Provide driver code suggestions for the UI
    - Expose popularity-ranked driver lists

    Pattern: Service Layer
    Principle: DIP – Presentation layer depends on this service, not on the
               repository directly. Keeps the DB layer hidden from the UI.
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self._repo = DriverRepository(db_path=db_path)

    def get_all_driver_codes(self) -> list[str]:
        """Returns all known driver codes, sorted alphabetically."""
        return self._repo.get_all_driver_codes()

    def get_popular_drivers(self, limit: int = 3) -> list[str]:
        """Returns the most frequently chosen driver codes."""
        return self._repo.get_popular_drivers(limit=limit)
