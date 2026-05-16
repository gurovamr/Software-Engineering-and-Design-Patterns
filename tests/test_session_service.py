import pandas as pd
from unittest.mock import Mock, patch

from session_service import EventCacheResult, SessionService
from data_loading import TelemetryBundle


def make_bundle(results=None, laps=None, telemetry=None):
    return TelemetryBundle(
        session_info={},
        results=results if results is not None else pd.DataFrame(),
        laps=laps if laps is not None else pd.DataFrame(),
        weather=pd.DataFrame(),
        telemetry=telemetry if telemetry is not None else pd.DataFrame(),
        track_status=pd.DataFrame(),
        session_status=pd.DataFrame(),
        race_control_messages=pd.DataFrame(),
    )


@patch('session_service.SessionRepository')
def test_load_session_overview_uses_local_if_laps_exist(mock_repo_cls):
    repo = Mock()
    bundle = make_bundle(laps=pd.DataFrame([{'LapNumber': 1}]))
    repo.load_session.return_value = bundle
    mock_repo_cls.return_value = repo
    service = SessionService('db.sqlite')
    result = service.load_session_overview(2024, 'Monza', 'Q')
    assert result.source == 'local'
    assert 'local database' in result.message


@patch('session_service.load_session_quick')
@patch('session_service.SessionRepository')
def test_load_session_overview_fetches_and_saves(mock_repo_cls, mock_load_quick):
    repo = Mock()
    repo.load_session.return_value = None
    mock_repo_cls.return_value = repo
    bundle = make_bundle(laps=pd.DataFrame([{'LapNumber': 1}]))
    mock_load_quick.return_value = bundle
    service = SessionService('db.sqlite', cache_dir='cache')
    result = service.load_session_overview(2024, 'Monza', 'Q')
    assert result.source == 'fastf1'
    repo.save_session.assert_called_once()


@patch('session_service.load_session_quick', side_effect=RuntimeError('boom'))
@patch('session_service.SessionRepository')
def test_load_session_overview_returns_partial_on_fetch_error(mock_repo_cls, _):
    repo = Mock()
    partial = make_bundle(results=pd.DataFrame([{'Driver': 'HAM'}]), laps=pd.DataFrame())
    repo.load_session.return_value = partial
    mock_repo_cls.return_value = repo
    service = SessionService('db.sqlite')
    result = service.load_session_overview(2024, 'Monza', 'Q')
    assert result.source == 'partial'
    assert 'partial local data' in result.message


@patch('session_service.load_driver_telemetry')
@patch('session_service.SessionRepository')
def test_load_driver_telemetry_uses_local_slice(mock_repo_cls, mock_load_driver):
    repo = Mock()
    telemetry = pd.DataFrame([{'Driver': 'HAM', 'Speed': 300}, {'Driver': 'VER', 'Speed': 310}])
    repo.load_session.return_value = make_bundle(telemetry=telemetry)
    mock_repo_cls.return_value = repo
    service = SessionService('db.sqlite')
    result = service.load_driver_telemetry(2024, 'Monza', 'Q', 'HAM')
    assert result.source == 'local'
    assert result.telemetry['Driver'].tolist() == ['HAM']
    mock_load_driver.assert_not_called()


@patch('session_service.load_driver_telemetry')
@patch('session_service.SessionRepository')
def test_load_driver_telemetry_fetches_when_missing(mock_repo_cls, mock_load_driver):
    repo = Mock()
    stored = make_bundle(results=pd.DataFrame([{'Driver': 'HAM'}]), laps=pd.DataFrame([{'LapNumber': 1}]), telemetry=pd.DataFrame())
    refreshed = make_bundle(results=stored.results, laps=stored.laps, telemetry=pd.DataFrame([{'Driver': 'HAM', 'Speed': 300}]))
    repo.load_session.side_effect = [stored, refreshed]
    mock_repo_cls.return_value = repo
    mock_load_driver.return_value = pd.DataFrame([{'Driver': 'HAM', 'Speed': 300}])
    service = SessionService('db.sqlite')
    result = service.load_driver_telemetry(2024, 'Monza', 'Q', 'HAM')
    assert result.source == 'fastf1'
    repo.save_session.assert_called_once()
    assert result.telemetry['Driver'].tolist() == ['HAM']


def test_event_cache_result_total_available():
    result = EventCacheResult(loaded=['Q'], already_local=['R', 'FP1'], unavailable=[], stopped_by_rate_limit=False)
    assert result.total_available == 3


def test_driver_slice_filters_driver():
    telemetry = pd.DataFrame([{'Driver': 'HAM'}, {'Driver': 'VER'}])
    result = SessionService._driver_slice(telemetry, 'VER')
    assert result['Driver'].tolist() == ['VER']
