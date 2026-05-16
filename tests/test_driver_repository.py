from driver_repository import DriverRepository


def test_upsert_driver_codes_normalizes_and_sorts(tmp_path):
    repo = DriverRepository(tmp_path / 'drivers.sqlite')
    repo.upsert_driver_codes([' ham ', 'VER', 'ham', '', ' NOR '])
    assert repo.get_all_driver_codes() == ['HAM', 'NOR', 'VER']


def test_upsert_driver_codes_empty_list_is_noop(tmp_path):
    repo = DriverRepository(tmp_path / 'drivers.sqlite')
    repo.upsert_driver_codes([])
    assert repo.get_all_driver_codes() == []
