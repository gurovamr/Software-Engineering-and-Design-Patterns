from __future__ import annotations

import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from src.data_loading import cache_session, get_schedule_events

DB_PATH = "data/f1.sqlite"


class DataLoader:
    """Downloads F1 session data on first login, then only checks for updates."""

    _lock = threading.Lock()
    _running = False
    _progress: str = ""
    _done: bool = False
    _current = 0
    _total = 0

    SESSIONS = ["R", "Q"]
    START_YEAR = 2018
    MAX_WORKERS = 8

    @classmethod
    def _task_key(cls, event: str, session_code: str) -> str:
        return f"{event}|{session_code}"

    @classmethod
    def start(cls, year: int | None = None):
        """Starts sync: current year first, then backwards to START_YEAR."""
        with cls._lock:
            if cls._running:
                return
            cls._running = True
            cls._done = False
            cls._progress = "Starting sync\u2026"
        t = threading.Thread(target=cls._sync_all, daemon=True)
        t.start()

    @classmethod
    def get_status(cls) -> dict:
        with cls._lock:
            return {
                "running": cls._running,
                "done": cls._done,
                "progress": cls._progress,
                "current": cls._current,
                "total": cls._total,
            }

    
    @classmethod
    def _sync_all(cls):
        """Syncs current year first, then backwards to START_YEAR."""
        try:
            cls._ensure_sync_table()
            current_year = date.today().year
            years = [current_year] + list(range(current_year - 1, cls.START_YEAR - 1, -1))
            for year in years:
                cls._sync_year(year)
            with cls._lock:
                cls._progress = "All data ready."
                cls._done = True
                cls._running = False
        except Exception as e:
            with cls._lock:
                cls._progress = f"Error: {e}"
                cls._running = False

    @classmethod
    def _sync_year(cls, year: int):
        """Syncs a single year (called by _sync_all)."""
        state = cls._get_sync_state(year)
        remote_events = get_schedule_events(year)
        expected_keys = {cls._task_key(ev, sc) for ev in remote_events for sc in cls.SESSIONS}
        synced_keys = set(state["synced_keys"]) if state else set()

        if state and state["complete"] and expected_keys == synced_keys:
            with cls._lock:
                cls._progress = f"{year}: up to date"
            return

        missing_keys = expected_keys - synced_keys
        tasks = []
        for ev in remote_events:
            for sc in cls.SESSIONS:
                if cls._task_key(ev, sc) in missing_keys:
                    tasks.append((year, ev, sc))

        if not tasks:
            cls._mark_complete(year, sorted(expected_keys))
            with cls._lock:
                cls._progress = f"{year}: up to date"
            return

        with cls._lock:
            cls._total = len(tasks)
            cls._current = 0

        def _download(task):
            y, event, session_code = task
            try:
                cache_session(y, event, session_code, cache_dir="cache")
                return task, True
            except Exception:
                return task, False

        SAVE_EVERY = 10
        with ThreadPoolExecutor(max_workers=cls.MAX_WORKERS) as pool:
            futures = {pool.submit(_download, t): t for t in tasks}
            for i, future in enumerate(as_completed(futures), 1):
                task, ok = future.result()
                synced_keys.add(cls._task_key(task[1], task[2]))
                with cls._lock:
                    cls._progress = f"Caching {year} ({i}/{cls._total})"
                    cls._current = i
                if i % SAVE_EVERY == 0 or i == len(tasks):
                    cls._save_sync_state(year, sorted(synced_keys), complete=False)

        cls._mark_complete(year, sorted(synced_keys))

  
    @staticmethod
    def _ensure_sync_table():
        conn = sqlite3.connect(DB_PATH)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(sync_state)").fetchall()}
        if "synced_events_json" not in cols:
            try:
                conn.execute("ALTER TABLE sync_state ADD COLUMN synced_events_json TEXT DEFAULT '[]'")
                conn.commit()
            except Exception:
                pass
        conn.close()

    @staticmethod
    def _get_sync_state(year: int) -> dict | None:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT complete, synced_events_json FROM sync_state WHERE year = ?", (year,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return {
            "complete": bool(row[0]),
            "synced_keys": json.loads(row[1]) if row[1] else [],
        }

    @staticmethod
    def _save_sync_state(year: int, keys: list[str], complete: bool):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO sync_state (year, session_codes_json, synced_events_json, complete, last_sync_at) "
            "VALUES (?, '[]', ?, ?, datetime('now')) "
            "ON CONFLICT(year) DO UPDATE SET synced_events_json=excluded.synced_events_json, "
            "complete=excluded.complete, last_sync_at=excluded.last_sync_at",
            (year, json.dumps(keys), int(complete)),
        )
        conn.commit()
        conn.close()

    @classmethod
    def _mark_complete(cls, year: int, keys: list[str]):
        cls._save_sync_state(year, keys, complete=True)
