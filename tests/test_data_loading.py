from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from src.data_loading import FastF1Source, SessionRequest, TelemetryBundle, _enable_fastf1_cache
from src.data_loading import TelemetryBundle


@patch('src.data_loading.fastf1.Cache.enable_cache')
def test_enable_fastf1_cache_creates_and_enables(mock_enable, tmp_path):
    path = _enable_fastf1_cache(tmp_path / 'cache')
    assert path.exists()
    mock_enable.assert_called_once()


def test_build_driver_map_returns_mapping():
    df = pd.DataFrame({'DriverNumber': ['44', '1'], 'Driver': ['HAM', 'VER']})
    result = FastF1Source.build_driver_map(df)
    assert result == {'44': 'HAM', '1': 'VER'}


def test_safe_copy_session_attr_returns_empty_on_error():
    session = SimpleNamespace()
    result = FastF1Source._safe_copy_session_attr(session, 'missing_attr')
    assert result.empty


def test_normalize_results_renames_columns():
    session = SimpleNamespace(
        results=pd.DataFrame({'Abbreviation': ['HAM'], 'TeamName': ['Mercedes'], 'Position': [1], 'DriverNumber': [44]}),
        event={'EventName': 'Monza', 'EventDate': pd.Timestamp('2024-09-01')},
        name='Race',
    )
    result = FastF1Source._normalize_results(session)
    assert 'Driver' in result.columns
    assert 'Team' in result.columns
    assert result.iloc[0]['EventName'] == 'Monza'
    assert result.iloc[0]['Year'] == 2024


def test_normalize_laps_adds_seconds_columns():
    laps = pd.DataFrame({
        'Driver': ['44'],
        'LapTime': [timedelta(seconds=91)],
        'Sector1Time': [timedelta(seconds=30)],
    })
    session = SimpleNamespace(laps=laps, event={'EventName': 'Monza'}, name='Race')
    result = FastF1Source._normalize_laps(session, driver_map={'44': 'HAM'})
    assert result.iloc[0]['Driver'] == 'HAM'
    assert result.iloc[0]['LapTimeSeconds'] == 91
    assert result.iloc[0]['EventName'] == 'Monza'


def test_merge_single_lap_telemetry_returns_empty_on_failure():
    lap = Mock()
    lap.get_car_data.side_effect = RuntimeError('nope')
    result = FastF1Source._merge_single_lap_telemetry(SimpleNamespace(event={'EventName': 'Monza'}, name='Race'), lap, True, None)
    assert result.empty


def test_telemetry_bundle_save_writes_parquet(tmp_path):
    bundle = TelemetryBundle(
        session_info={},
        results=pd.DataFrame([{'x': 1}]),
        laps=pd.DataFrame([{'x': 1}]),
        weather=pd.DataFrame([{'x': 1}]),
        telemetry=pd.DataFrame([{'x': 1}]),
        track_status=pd.DataFrame([{'x': 1}]),
        session_status=pd.DataFrame([{'x': 1}]),
        race_control_messages=pd.DataFrame([{'x': 1}]),
    )
    bundle.save(tmp_path)
    assert (tmp_path / 'results.parquet').exists()
    assert (tmp_path / 'telemetry.parquet').exists()
