from src.database.base_repository import BaseRepository


class DriverRepository(BaseRepository):
    """
    Handles all driver-related database queries.

    Responsibilities:
    - Create and migrate the drivers schema
    - Retrieve all unique driver codes stored locally

    Pattern: Repository
    """

    def ensure_schema(self) -> None:
        """Creates the drivers table if it does not already exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS drivers (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_code TEXT    UNIQUE NOT NULL,
                    full_name   TEXT,
                    team        TEXT,
                    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get_all_driver_codes(self) -> list[str]:
        """Returns all unique driver codes found in the drivers table."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT driver_code FROM drivers ORDER BY driver_code"
                ).fetchall()
            return [row[0] for row in rows if row[0]]
        except Exception:
            return []
