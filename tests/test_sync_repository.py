from sync_repository import SyncRepository


def test_save_and_get_state(tmp_path):
    repo = SyncRepository(tmp_path / 'sync.sqlite')
    repo.ensure_schema()
    repo.save_state(2024, ['Monza|Q'], complete=False)
    state = repo.get_state(2024)
    assert state == {'complete': False, 'synced_keys': ['Monza|Q']}


def test_mark_complete_sets_complete_flag(tmp_path):
    repo = SyncRepository(tmp_path / 'sync.sqlite')
    repo.ensure_schema()
    repo.mark_complete(2024, ['Monza|R'])
    state = repo.get_state(2024)
    assert state == {'complete': True, 'synced_keys': ['Monza|R']}
