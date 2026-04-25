from src.database.base_repository import BaseRepository


class DriverRepository(BaseRepository):
    """
    Handles all driver-related database queries.

    Responsibilities:
    - Retrieve all unique driver codes from telemetry sessions
    - Determine popular drivers by login frequency

    Pattern: Repository
    """

    def get_all_driver_codes(self) -> list[str]:
        """Returns all unique driver codes found in the results table."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT driver_code FROM drivers ORDER BY driver_code"
                ).fetchall()
            return [row[0] for row in rows if row[0]]
        except Exception:
            return []

    def get_popular_drivers(self, limit: int = 3) -> list[str]:
        """
        Returns the most frequently chosen driver codes as favorites.

        Uses the users table to count how often each driver was selected.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT favorite_driver, COUNT(*) as cnt
                FROM users
                WHERE favorite_driver IS NOT NULL AND favorite_driver != ''
                GROUP BY favorite_driver
                ORDER BY cnt DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [row[0] for row in rows]
