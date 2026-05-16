import sqlite3
from pathlib import Path

from src.database.base_repository import BaseRepository


class DummyRepository(BaseRepository):
    pass


def test_connect_creates_parent_directory_and_commits(tmp_path):
    db_path = tmp_path / 'nested' / 'test.sqlite'
    repo = DummyRepository(db_path)
    with repo._connect() as conn:
        conn.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)')
        conn.execute('INSERT INTO sample (name) VALUES (?)', ('x',))
    assert db_path.exists()
    with sqlite3.connect(db_path) as conn:
        row = conn.execute('SELECT name FROM sample').fetchone()
    assert row[0] == 'x'
