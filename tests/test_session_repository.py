import pandas as pd

from src.database.session_repository import SessionRepository
from src.data_loading import TelemetryBundle


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


def test_df_json_roundtrip():
    df = pd.DataFrame({'Driver': ['HAM'], 'Time': [1.2]})
    payload = SessionRepository._df_to_json(df)
    restored = SessionRepository._json_to_df(payload)
    assert restored.iloc[0]['Driver'] == 'HAM'


def test_merge_telemetry_deduplicates():
    existing = pd.DataFrame([{'Driver': 'HAM', 'LapNumber': 1, 'Time': 1, 'Distance': 10, 'Speed': 300}])
    incoming = pd.DataFrame([{'Driver': 'HAM', 'LapNumber': 1, 'Time': 1, 'Distance': 10, 'Speed': 301}])
    merged = SessionRepository._merge_telemetry(existing, incoming)
    assert len(merged) == 1
    assert merged.iloc[0]['Speed'] == 301


def test_save_and_load_session(tmp_path):
    repo = SessionRepository(tmp_path / 'sessions.sqlite')
    bundle = make_bundle(
        results=pd.DataFrame([{'Driver': 'HAM'}]),
        laps=pd.DataFrame([{'LapNumber': 1}]),
        telemetry=pd.DataFrame([{'Driver': 'HAM', 'LapNumber': 1, 'Time': 1, 'Distance': 10}]),
    )
    repo.save_session(2024, 'Monza', 'Q', bundle)
    loaded = repo.load_session(2024, 'Monza', 'Q')
    assert loaded is not None
    assert loaded.results.iloc[0]['Driver'] == 'HAM'
    assert loaded.laps.iloc[0]['LapNumber'] == 1
