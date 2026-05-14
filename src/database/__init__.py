from src.database.base_repository import BaseRepository
from src.database.driver_repository import DriverRepository
from src.database.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "DriverRepository",
    "F1DriverQuery",
    "F1TrackQuery",
    "SyncRepository",
    "TrackRepository",
    "UserRepository",
]


def __getattr__(name):
    if name == "F1DriverQuery":
        from src.database.drivers import F1DriverQuery

        return F1DriverQuery
    if name == "F1TrackQuery":
        from src.database.tracks import F1TrackQuery

        return F1TrackQuery
    if name == "SyncRepository":
        from src.database.sync_repository import SyncRepository

        return SyncRepository
    if name == "TrackRepository":
        from src.database.track_repository import TrackRepository

        return TrackRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
