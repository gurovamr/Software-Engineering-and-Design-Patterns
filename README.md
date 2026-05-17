<a id="readme-top"></a>

<div align="center">

# Software Engineering and Design Patterns

![GitHub Repo Badge](https://img.shields.io/badge/github-repo-blue?logo=github)
[![License: Unlicense](https://img.shields.io/badge/License-Unlicense-blue.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Python CI/CD](https://github.com/gurovamr/Software-Engineering-and-Design-Patterns/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/gurovamr/Software-Engineering-and-Design-Patterns/actions/workflows/ci-cd.yml)
[![Dash](https://img.shields.io/badge/Dash-Plotly-blue?logo=plotly&logoColor=white)](https://dash.plotly.com/)

Formula 1 telemetry dashboard built for the ZHAW Master in Life Sciences course
*Software Engineering and Design Patterns*, Spring 2026.

</div>

## Table of Contents

- [About](#about)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Design Notes](#design-notes)
- [Roadmap](#roadmap)
- [Authors](#authors)
- [License](#license)

## About

The project visualizes real Formula 1 session data with a Dash dashboard. It combines race overview charts, lap selection, telemetry plots, and spatial track maps so selected drivers can be compared across the same parts of a lap.

The application uses FastF1 data, stores loaded sessions in a local SQLite database, and separates the UI, callbacks, services, repositories, telemetry helpers, and visualization classes to demonstrate object-oriented design and design pattern principles.

[Back to top](#readme-top)

## Features

- Login and optional favorite-driver selection.
- Session loading by year, event, and session type.
- Local SQLite caching for session and telemetry data.
- Race overview with finishing order, podium cards, key events, tyre strategy, team pace, lap-time distribution, and position chart.
- Driver analysis for up to three selected drivers.
- Per-driver lap tables showing the 10 fastest laps by default.
- `Show all laps` checkbox directly above the lap tables.
- Telemetry charts for speed, gear, throttle, and brake over distance.
- Track-map lap selectors for each selected driver.
- Track map colored by speed and gear-shift track map.
- Client-side cross-hover on track maps: hovering a point for one driver highlights the nearest distance-matched point for the other selected drivers and shows comparable metrics in persistent annotation boxes.

[Back to top](#readme-top)

## Project Structure

```text
.
|-- app_dash.py          # Dash application entry point
|-- assets/              # Dash CSS and client-side JavaScript assets
|   |-- dashboard.css
|   `-- track_hover_sync.js
|-- cache/               # FastF1/cache files created locally
|-- data/                # Local SQLite database and project data
|-- docs/                # UML, class overview, and generated documentation
|-- notebooks/           # Exploration and prototyping notebooks
|-- src/                 # Application source code
|   |-- dash_layout.py
|   |-- dash_callbacks.py
|   |-- session_service.py
|   |-- telemetry_metrics.py
|   |-- visualization.py
|   `-- ...
|-- tests/               # Unit and layout tests
|-- environment.yml      # Conda environment definition
|-- requirements-dev.txt # Development dependencies
`-- README.md
```

[Back to top](#readme-top)

## Getting Started

### Prerequisites

- Git
- Conda
- Python 3.10+

### Installation

```sh
git clone https://github.com/gurovamr/Software-Engineering-and-Design-Patterns
cd Software-Engineering-and-Design-Patterns
conda env create -f environment.yml
conda activate SEDP
```

If you use `requirements-dev.txt` instead of Conda, install the listed dependencies into a Python environment that includes Dash, Plotly, pandas, numpy, FastF1, and the test tools.

[Back to top](#readme-top)

## Usage

Run the Dash dashboard:

```sh
python app_dash.py
```

Open the local URL shown by Dash, usually:

```text
http://127.0.0.1:8050/
```

Typical workflow:

1. Log in or register a local user.
2. Select a year, race/event, and session.
3. Click `Load Session`.
4. Select up to three drivers in the finishing-order table.
5. Use the lap tables to select exact laps for telemetry plots.
6. Use `Show all laps` if the default 10 fastest laps are not enough.
7. Choose track-map laps for the selected drivers.
8. Hover on a speed or gear track map to compare the same distance point across drivers.

If JavaScript or CSS changes do not appear in the browser, hard-refresh the page with `Ctrl + F5`.

[Back to top](#readme-top)

## Design Notes

- `DashboardCallbackRegistry` acts as the callback facade/controller for the Dash app.
- `DashLayout` builds the component tree for login, session controls, race overview, driver analysis, telemetry plots, and track-map controls.
- `SessionService` provides a service layer over local storage and FastF1 loading.
- Repository classes persist session data in SQLite.
- Visualization classes encapsulate Plotly chart creation.
- `assets/track_hover_sync.js` implements track-map cross-hover in the browser to avoid slow server-side figure rebuilds on every mouse movement.

[Back to top](#readme-top)

## Roadmap

- [x] Initialize repository and README backbone
- [x] Add F1 data loading
- [x] Build the Dash dashboard
- [x] Add local storage with SQLite
- [x] Implement OOD principles and design patterns
- [x] Add per-driver lap selection
- [x] Add track-map cross-hover comparison
- [x] Add a pipeline with unit testing.

[Back to top](#readme-top)

## Authors

- **Mariiia Gurova**
  - GitHub: [@gurovamr](https://github.com/gurovamr)
- **Pia Lagler**
  - GitHub: [@Lagpi](https://github.com/Lagpi)
- **Kai Aebli**
  - GitHub: [@aeblik](https://github.com/aeblik)
- **Spyridon Margomenos**
  - GitHub: [@the-nerd-sloth](https://github.com/the-nerd-sloth)

[Back to top](#readme-top)

## License

Distributed under The Unlicense license. For more information see [LICENSE](./LICENSE).

[Back to top](#readme-top)
