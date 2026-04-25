from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from src.data_loading import cache_session
from src.database import F1TrackQuery, TrackRepository
from src.database.sync_repository import SyncRepository

DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "f1.sqlite")
CACHE_DIR = str(Path(__file__).resolve().parent.parent / "cache")


class DataLoader:
    """
    Downloads F1 session data on first login, then only checks for updates.

    Pattern: Singleton - only one sync process runs process-wide.
    """

    _instance: DataLoader | None = None
    _creation_lock = threading.Lock()

    SESSIONS = ["R", "Q"]
    START_YEAR = 2018
    MAX_WORKERS = 8
    SAVE_EVERY = 10

    # ── Singleton constructor ───────────────────────────────────────────────

    def __new__(cls) -> DataLoader:
        with cls._creation_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._state_lock = threading.Lock()
                instance._running: bool = False
                instance._progress: str = ""
                instance._done: bool = False
                instance._current: int = 0
                instance._total: int = 0
                cls._instance = instance
        return cls._instance

    # ── Public API ─────────────────────────────────────────────────────────

    def begin_sync(self, year: int | None = None) -> None:
        """Starts sync from the given year (or current year) backwards to START_YEAR."""
        with self._state_lock:
            if self._running:
                return
            self._running = True
            self._done = False
            self._progress = "Starting sync\u2026"
        threading.Thread(target=self._run_full_sync, args=(year,), daemon=True).start()

    def get_sync_status(self) -> dict:
        """Returns a snapshot of the current sync state."""
        with self._state_lock:
            return {
                "running": self._running,
                "done": self._done,
                "progress": self._progress,
                "current": self._current,
                "total": self._total,
            }

    # ── Internal sync logic ────────────────────────────────────────────────

    @classmethod
    def _make_session_task_key(cls, event: str, session_code: str) -> str:
        return f"{event}|{session_code}"

    def _run_full_sync(self, year: int | None = None) -> None:
        """Syncs from the given year (or current year) backwards to START_YEAR."""
        try:
            _sync_repo = SyncRepository(DB_PATH)
            _sync_repo.ensure_schema()
            current_year = year if year is not None else date.today().year
            years = [current_year] + list(range(current_year - 1, self.START_YEAR - 1, -1))
            for year in years:
                self._sync_year_sessions(year, _sync_repo)
            with self._state_lock:
                self._progress = "All data ready."
                self._done = True
                self._running = False
        except Exception as e:
            with self._state_lock:
                self._progress = f"Error: {e}"
                self._running = False

    def _sync_year_sessions(self, year: int, sync_repo: SyncRepository) -> None:
        """Syncs a single year (called by _sync_all)."""
        state = sync_repo.get_state(year)

        # Cache-first: serve event list from local DB; only call FastF1 if empty
        track_repo = TrackRepository(DB_PATH)
        remote_events = track_repo.get_events(year)
        if not remote_events:
            remote_events = F1TrackQuery.from_schedule(year)
            if remote_events:
                track_repo.upsert_event_names(year, remote_events)
        expected_keys = {self._make_session_task_key(ev, sc) for ev in remote_events for sc in self.SESSIONS}
        synced_keys = set(state["synced_keys"]) if state else set()

        if state and state["complete"] and expected_keys == synced_keys:
            with self._state_lock:
                self._progress = f"{year}: up to date"
            return

        missing_keys = expected_keys - synced_keys
        tasks = [
            (year, ev, sc)
            for ev in remote_events
            for sc in self.SESSIONS
            if self._make_session_task_key(ev, sc) in missing_keys
        ]

        if not tasks:
            sync_repo.mark_complete(year, sorted(expected_keys))
            with self._state_lock:
                self._progress = f"{year}: up to date"
            return

        with self._state_lock:
            self._total = len(tasks)
            self._current = 0

        def _download(task):
            y, event, session_code = task
            try:
                cache_session(y, event, session_code, cache_dir=CACHE_DIR)
                return task, True
            except Exception:
                return task, False

        SAVE_EVERY = self.SAVE_EVERY
        all_ok = True
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as pool:
            futures = {pool.submit(_download, t): t for t in tasks}
            for i, future in enumerate(as_completed(futures), 1):
                task, ok = future.result()
                if ok:
                    synced_keys.add(self._make_session_task_key(task[1], task[2]))
                else:
                    all_ok = False
                with self._state_lock:
                    self._progress = f"Caching {year} ({i}/{self._total})"
                    self._current = i
                if i % SAVE_EVERY == 0 or i == len(tasks):
                    sync_repo.save_state(year, sorted(synced_keys), complete=False)

        if all_ok:
            sync_repo.mark_complete(year, sorted(synced_keys))
        else:
            sync_repo.save_state(year, sorted(synced_keys), complete=False)

    # DB concerns fully delegated to SyncRepository – no raw SQLite here.
