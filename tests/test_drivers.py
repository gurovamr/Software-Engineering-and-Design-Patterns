from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from src.database.drivers import F1DriverQuery


def test_from_laps_returns_sorted_unique_drivers():
    laps = pd.DataFrame({'Driver': ['VER', ' HAM ', 'VER', None]})
    assert F1DriverQuery.from_laps(laps) == ['HAM', 'VER']


def test_from_results_prefers_first_available_column():
    results = pd.DataFrame({'Abbreviation': ['VER', 'HAM', 'VER']})
    assert F1DriverQuery.from_results(results) == ['HAM', 'VER']


@patch('src.drivers.load_session_quick')
def test_for_session_uses_results_then_laps(mock_load):
    mock_load.return_value = SimpleNamespace(
        results=pd.DataFrame({'Driver': ['VER', 'HAM']}),
        laps=pd.DataFrame({'Driver': ['NOR']})
    )
    assert F1DriverQuery.for_session(2024, 'Monza', 'Q') == ['HAM', 'VER']
