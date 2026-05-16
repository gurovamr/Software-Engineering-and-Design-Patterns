# Class Overview

This table summarizes the main classes and class-like modules used in the F1 telemetry dashboard. It is intended as a compact report companion to `uml_description.puml`.

## Relationship Legend

| Term | Meaning in this project |
| --- | --- |
| Generalization / inheritance | A concrete class extends an abstract base class, for example `SpeedChart` extends `BaseChart`. |
| Polymorphism | Different subclasses share the same public contract, for example all `BaseChart` subclasses implement `_build()` and are rendered through `render()`. |
| Composition | A class owns another object as an internal part, for example `AuthService` owns a `UserRepository`. |
| Association | A class collaborates with another class during normal execution. |
| Dependency | A weaker "uses" relation, often through method calls, static helpers, or temporary objects. |
| Facade | A class/module exposes a simpler interface over more complex behavior. |
| Adapter | A class wraps an external API and converts it into the project's own model. |

## Classes

| Class / Module | Layer | Key attributes | Key methods | Relationship / pattern | Short description |
| --- | --- | --- | --- | --- | --- |
| `DashApp` (`app_dash.py`) | Application | Injected service instances, `app`, `server` | Dash initialization code | Composition root; dependency injection setup | Creates Dash app, constructs services once, builds layout, and registers callbacks. |
| `DashboardCallbackRegistry` | Application / Controller | `_auth`, `_driver_repo`, `_loader`, `_session_service`, `_session_cache` | `register()`, `_store_session_bundle()`, `_retrieve_cached_bundle()`, `_drivers_from_selected_rows()`, `_top_lap_table_for_driver()`, `_telemetry_from_lap_rows()`, `_track_telemetry_for_drivers()` | Facade/controller; associations with services, telemetry helpers, and chart classes | Registers all Dash callbacks and coordinates authentication, DB-first session loading, per-driver lap selection, telemetry metrics, and chart generation. |
| `DashLayout` (`dash_layout.py`) | Application / UI module | Theme constants such as `_BG`, `_CARD_BG`, `_ACCENT` | `create_layout()`, `empty_fig()`, `_login_page()`, `_dashboard_page()`, `_results_table()`, `_lap_table_panel()` | UI factory module; dependency on Dash components | Builds the Dash component tree for login, sidebar, race overview, driver selection, per-driver lap tables, telemetry plots, and track-map controls. |
| `AuthService` | Domain service | `_repo: UserRepository` | `register()`, `login()`, `update_favorite_driver()` | Composition with `UserRepository`; Service Layer | Handles registration, password verification, login, and favorite-driver updates. |
| `DriverService` | Domain service | `_repo: DriverRepository`, `_user_repo: UserRepository` | `get_all_driver_codes()`, `save_driver_codes()`, `refresh_known_driver_codes()`, `get_popular_drivers()` | Composition with `DriverRepository`; association with `UserRepository`; Service Layer | Provides driver suggestions, persists discovered driver codes, refreshes missing driver data on demand, and exposes popularity information without exposing database queries to the UI. |
| `SessionService` | Domain service | `_repo: SessionRepository`, `_cache_dir` | `load_session_overview()`, `load_driver_telemetry()`, `cache_full_event()`, `_driver_slice()` | Service Layer / DB-first facade; composition with `SessionRepository`; dependency on FastF1 wrapper functions | Loads sessions from local SQLite first, fetches missing overview or driver telemetry from FastF1 only when needed, merges telemetry into the local database, and caches full event overviews. |
| `TelemetryService` | Domain service | `_df: DataFrame` | `get_available_drivers()`, `get_driver_laps()`, `get_multiple_laps_telemetry()`, `get_lap_summary()`, `build_results_table()` | Service; module-level wrapper functions delegate to it | Encapsulates telemetry filtering, lap selection, fastest-lap lookup, summaries, and result table formatting. |
| `PitStopExtractor` | Domain service | None | `extract()` | Stateless utility service | Extracts pit stop events from lap data for dashboard event badges. |
| `DataLoader` | Domain service / Background sync | `_running`, `_progress`, `_done`, `_current`, `_total`, `_state_lock` | `__new__()`, `begin_sync()`, `get_sync_status()`, `_run_full_sync()`, `_sync_year_sessions()` | Singleton; association with `SyncRepository`, `F1ScheduleService`, and cache preload | Runs one process-wide background synchronization of F1 session data. |
| `BaseRepository` | Persistence | `_db_path` | `_connect()` | Abstract base class; Repository base | Provides shared SQLite connection handling for concrete repositories. |
| `UserRepository` | Persistence | Inherited `_db_path` | `ensure_schema()`, `find_by_name()`, `exists()`, `create()`, `update_favorite_driver()`, `log_login()`, `hash_password()`, `verify_password()` | Inherits `BaseRepository`; Repository pattern | Owns SQL operations for users, password hashes, favorite drivers, and login events. |
| `DriverRepository` | Persistence | Inherited `_db_path` | `ensure_schema()`, `upsert_driver_codes()`, `get_all_driver_codes()` | Inherits `BaseRepository`; Repository pattern | Creates and reads the local driver-code table and stores driver codes discovered from loaded sessions. |
| `TrackRepository` | Persistence | Inherited `_db_path` | `ensure_schema()`, `get_events()`, `upsert_events()`, `upsert_event_names()` | Inherits `BaseRepository`; Repository pattern | Stores schedule event names locally so event dropdowns can load cache-first and avoid unnecessary FastF1 calls. |
| `SessionRepository` | Persistence | Inherited `_db_path` | `ensure_schema()`, `load_session()`, `save_session()`, `_merge_telemetry()`, `_df_to_json()`, `_json_to_df()` | Inherits `BaseRepository`; Repository pattern; local SQLite cache | Persists session overview data and on-demand telemetry in `sessions`; migrates older local databases by adding missing `session_info`; stores DataFrames as JSON strings. |
| `SyncRepository` | Persistence | Inherited `_db_path` | `ensure_schema()`, `get_state()`, `save_state()`, `mark_complete()` | Inherits `BaseRepository`; Repository pattern | Persists yearly synchronization state for background caching. |
| `F1DriverQuery` | F1 data query helper | None | `from_laps()`, `from_results()`, `for_session()` | Query Object / Static Helper; dependency on session loading wrapper | Extracts driver codes from loaded lap/results data or from a specific FastF1 session without exposing FastF1 details to UI code. |
| `F1TrackQuery` | F1 data query helper | None | `from_schedule()`, `with_lap_data()` | Query Object / Static Helper; dependency on schedule and lap availability wrappers | Provides schedule/event-name lookup and optional lap-data availability checks through FastF1-backed helper functions. |
| `SessionRequest` | Data model | `year`, `event`, `session_code`, `drivers`, `fastest_lap_only`, `include_weather`, `include_messages`, `add_distance` | Dataclass-generated methods | Value Object | Immutable request object describing which F1 session and telemetry options to load. |
| `TelemetryBundle` | Data model | `session_info`, `results`, `laps`, `weather`, `telemetry`, `track_status`, `session_status`, `race_control_messages` | `save()` | DTO | Aggregates normalized DataFrames returned from one F1 session load. |
| `SessionLoadResult` | Data model | `bundle`, `source`, `message` | Dataclass-generated methods | DTO | Describes whether a session overview came from SQLite, FastF1, or partial local data and carries a user-facing status message. |
| `DriverTelemetryResult` | Data model | `bundle`, `telemetry`, `source`, `message` | Dataclass-generated methods | DTO | Describes whether driver telemetry came from SQLite or FastF1 and carries the updated session bundle. |
| `EventCacheResult` | Data model | `loaded`, `already_local`, `unavailable`, `stopped_by_rate_limit`, `total_available` | Dataclass-generated methods plus property | DTO | Summarizes the result of caching all available sessions for one event. |
| `TelemetrySource` | F1 data layer | None | `load_bundle()` | Abstract base class; polymorphic source interface | Defines the common loading contract for telemetry data sources. |
| `_enable_fastf1_cache()` | F1 data layer | None | `_enable_fastf1_cache(cache_dir)` | Utility function; dependency from FastF1-facing classes | Creates the cache directory before enabling FastF1 cache, preventing startup errors on fresh checkouts where `cache/` does not yet exist. |
| `FastF1Source` | F1 data layer | `_cache_dir` | `load_bundle()`, `build_driver_map()`, `_normalize_results()`, `_normalize_laps()`, `_build_telemetry_dataframe()` | Inherits `TelemetrySource`; Adapter pattern; dependency on `_enable_fastf1_cache()` | Wraps the external FastF1 API, ensures cache setup, and normalizes sessions into project DataFrames. |
| `F1SessionBundleCache` | F1 data layer | `_cache_dir`, `_cache` | `load_quick()`, `load_driver_telemetry()`, `load_full()`, `preload()` | Facade / cache; composition with `FastF1Source`; creates `SessionRequest` and returns `TelemetryBundle` | Provides high-level session loading, on-demand telemetry extraction, and FastF1 session reuse. |
| `F1ScheduleService` | F1 data layer | Shared `_event_cache`, `_cache_dir` | `get_events()`, `get_events_with_laps()` | Monostate; dependency on FastF1 and `_enable_fastf1_cache()` | Provides cached event schedule lookup where all instances share the same state and ensures the FastF1 cache directory exists before schedule calls. |
| `DarkThemeConfig` | Visualization | `bg`, `grid`, `text` | Dataclass-generated methods | Value Object; aggregation by chart bases | Stores reusable theme colors for Plotly chart styling. |
| `F1ColorPalette` | Visualization | Team, compound, and gear color maps | `get_team_color()`, `get_compound_color()`, `get_gear_color()`, `hex_to_rgba()` | Utility class; dependency from chart classes | Centralizes F1-specific colors for teams, tyres, gears, and comparison charts. |
| `BaseChart` | Visualization | `_df`, `_theme` | `render()`, `_build()`, `_apply_theme()`, `empty_figure()` | Abstract base; Template Method; polymorphism | Defines the common chart rendering workflow. Subclasses implement `_build()`, while `render()` applies shared styling. |
| `SpeedChart` | Visualization | Inherited `_df` | `_build()` | Inherits `BaseChart`; polymorphic chart implementation | Builds a speed-over-distance line chart. |
| `LapSummaryChart` | Visualization | Inherited `_df` | `_build()` | Inherits `BaseChart`; polymorphic chart implementation | Builds a lap-time comparison chart across selected laps. |
| `ThrottleBrakeChart` | Visualization | Inherited `_df` | `_build()` | Inherits `BaseChart`; polymorphic chart implementation | Plots throttle and brake input traces over distance. |
| `GearChart` | Visualization | Inherited `_df` | `_build()` | Inherits `BaseChart`; polymorphic chart implementation | Plots gear number over distance for selected laps. |
| `TrackMapChart` | Visualization | Inherited `_df` | `_build()` | Inherits `BaseChart`; polymorphic chart implementation | Builds a track map colored by speed. |
| `PositionChart` | Visualization | Inherited `_df` | `_build()` | Inherits `BaseChart`; dependency on `F1ColorPalette` | Builds race position traces by driver and marks pit stops. |
| `TyreStrategyChart` | Visualization | Inherited `_df` | `_build()` | Inherits `BaseChart`; dependency on `F1ColorPalette` | Builds a stacked horizontal bar chart for tyre stints. |
| `TeamPaceChart` | Visualization | Inherited `_df` | `_build()` | Inherits `BaseChart`; dependency on `F1ColorPalette` | Compares team lap-time distributions using box plots. |
| `LapTimesDistributionChart` | Visualization | `_top_n`, inherited `_df` | `__init__()`, `_build()` | Inherits `BaseChart`; polymorphic chart implementation | Shows lap-time distributions for top drivers with violin plots. |
| `GearMapChart` | Visualization | Inherited `_df` | `_build()` | Inherits `BaseChart`; dependency on `F1ColorPalette` | Visualizes gear usage spatially on the track map. |
| `TwoDriverChart` | Visualization | `_tel1`, `_tel2`, `_driver1`, `_driver2`, `_theme` | `render()`, `_build()`, `_apply_theme()` | Abstract base; Template Method; polymorphism | Defines the common rendering workflow for charts comparing exactly two drivers. |
| `DriverComparisonChart` | Visualization | `_title`, `_lap_time1`, `_lap_time2`, inherited telemetry fields | `_build()`, `_compute_delta()`, `_build_delta_subtitle()` | Inherits `TwoDriverChart`; dependency on `F1ColorPalette` | Builds a multi-row telemetry comparison chart and computes time delta between two drivers. |

## Design Pattern Summary

| Pattern / principle | Implemented by | Purpose |
| --- | --- | --- |
| Repository | `BaseRepository`, `UserRepository`, `DriverRepository`, `TrackRepository`, `SessionRepository`, `SyncRepository` | Separates database access from services and UI code. |
| Service Layer | `AuthService`, `DriverService`, `SessionService`, `TelemetryService`, `DataLoader` | Keeps business/application logic outside UI callbacks. |
| Adapter | `FastF1Source` | Shields the app from direct dependence on FastF1 internals. |
| Facade | `SessionService`, `F1SessionBundleCache`, `DashboardCallbackRegistry` | Provides simpler interfaces over database-first loading, caching, data loading, or callback orchestration. |
| Query Object / Static Helper | `F1DriverQuery`, `F1TrackQuery` | Collects read-only FastF1-backed lookup logic for drivers and event metadata. |
| Singleton | `DataLoader` | Ensures only one background sync process runs per Python process. |
| Monostate | `F1ScheduleService` | Allows multiple instances while sharing one event cache. |
| DTO / Value Object | `TelemetryBundle`, `SessionRequest`, `SessionLoadResult`, `DriverTelemetryResult`, `EventCacheResult`, `DarkThemeConfig` | Moves structured data between layers with minimal behavior. |
| Template Method | `BaseChart`, `TwoDriverChart` | Shared `render()` workflow delegates chart-specific construction to `_build()`. |
| Polymorphism | All `BaseChart` and `TwoDriverChart` subclasses | UI code can render different chart objects through a common interface. |
| Dependency Injection | `app_dash.py`, `DashboardCallbackRegistry` | Services are created once and injected into the callback registry. |
| Local cache first | `TrackRepository`, `SessionRepository`, `SessionService`, `_enable_fastf1_cache()` | Uses local SQLite/FastF1 cache before network calls and creates required local directories/schemas automatically. |

## Current Dash Data Flow

| Flow | Main classes/modules | Summary |
| --- | --- | --- |
| Event dropdown | `DashboardCallbackRegistry`, `TrackRepository`, `F1ScheduleService` | Reads cached event names from SQLite first; if missing, fetches the schedule from FastF1 and stores event names locally. |
| Load Session | `DashboardCallbackRegistry`, `SessionService`, `SessionRepository`, `F1SessionBundleCache` | Loads session overview from SQLite when possible; otherwise fetches results and lap data from FastF1 and stores them in `sessions`. |
| Load Full Event | `DashboardCallbackRegistry`, `SessionService`, `EventCacheResult` | Attempts all known session codes for one event and stores available session overviews locally without fetching full telemetry for every driver. |
| Driver analysis | `DashboardCallbackRegistry`, `DashLayout`, telemetry helper functions | The finishing-order table selects up to three drivers; the lap-time graph shows all laps for those drivers; each selected driver gets a top-10 fastest-lap table. |
| Telemetry plots | `DashboardCallbackRegistry`, `SessionService`, `SessionRepository`, chart classes | The fastest lap in each driver table is selected by default; selected table rows control speed, gear, throttle/brake telemetry; missing driver telemetry is fetched on demand and merged into SQLite. |
| Track maps | `DashboardCallbackRegistry`, per-driver track lap dropdowns | Each selected driver gets a track-map lap dropdown, defaulting to the fastest lap; speed and gear track maps display selected drivers side by side. |
