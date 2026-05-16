import pytest

from src.database.track_repository import TrackRepository


def test_upsert_and_get_events(tmp_path):
    repo = TrackRepository(tmp_path / 'tracks.sqlite')
    repo.upsert_events(2024, [
        {'event_name': 'Monza', 'round_number': 16},
        {'event_name': 'Spa', 'round_number': 14},
    ])
    assert repo.get_events(2024) == ['Spa', 'Monza']


def test_upsert_event_names(tmp_path):
    repo = TrackRepository(tmp_path / 'tracks.sqlite')
    repo.upsert_event_names(2024, ['Monza', 'Spa'])
    assert sorted(repo.get_events(2024)) == ['Monza', 'Spa']


def test_upsert_events_requires_event_name(tmp_path):
    repo = TrackRepository(tmp_path / 'tracks.sqlite')
    with pytest.raises(ValueError):
        repo.upsert_events(2024, [{'round_number': 1}])
