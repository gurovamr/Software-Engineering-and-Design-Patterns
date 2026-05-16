from user_repository import UserRepository


def test_create_find_exists_update_and_popular(tmp_path):
    repo = UserRepository(tmp_path / 'users.sqlite')
    repo.ensure_schema()
    user_id = repo.create('alice', 'hash1', 'HAM')
    repo.create('bob', 'hash2', 'HAM')
    assert repo.exists('alice') is True
    assert repo.find_by_name('alice')['id'] == user_id
    repo.update_favorite_driver(user_id, 'VER')
    assert repo.find_by_name('alice')['favorite_driver'] == 'VER'
    assert repo.get_popular_drivers(limit=2)[0] in {'HAM', 'VER'}


def test_log_login_records_event(tmp_path):
    repo = UserRepository(tmp_path / 'users.sqlite')
    repo.ensure_schema()
    user_id = repo.create('alice', 'hash1', None)
    repo.log_login(user_id)
    with repo._connect() as conn:
        count = conn.execute('SELECT COUNT(*) FROM login_events WHERE user_id = ?', (user_id,)).fetchone()[0]
    assert count == 1
