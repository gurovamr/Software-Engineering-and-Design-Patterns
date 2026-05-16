from unittest.mock import patch

from src.database.tracks import F1TrackQuery


@patch('src.database.tracks.get_schedule_events', return_value=['Monza', 'Spa'])
def test_from_schedule_delegates(mock_get):
    assert F1TrackQuery.from_schedule(2024) == ['Monza', 'Spa']
    mock_get.assert_called_once_with(2024)


@patch('src.database.tracks.get_events_with_available_laps', return_value=['Monza'])
def test_with_lap_data_delegates(mock_get):
    result = F1TrackQuery.with_lap_data(2024, 'Q', cache_dir='cache')
    assert result == ['Monza']
    mock_get.assert_called_once()
