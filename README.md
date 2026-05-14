<a id="readme-top"></a>

<div align="center">

# Software Engineering and Design Patterns

![GitHub Repo Badge](https://img.shields.io/badge/github-repo-blue?logo=github)
[![License: Unlicense](https://img.shields.io/badge/License-Unlicense-blue.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

This is the group project for the course of *Software Engineering and Design Patterns*, for the Spring 2026 semester of the ZHAW Master in Life Sciences.

The main purpose of this project is to apply the theory of the course, while incrementally designing and documenting a software system across multiple development stages.


</div>

## Table of Contents

- [Software Engineering and Design Patterns](#software-engineering-and-design-patterns)
	- [Table of Contents](#table-of-contents)
	- [About](#about)
	- [Goals](#goals)
	- [Project Structure](#project-structure)
	- [Getting Started](#getting-started)
		- [Prerequisites](#prerequisites)
		- [Installation](#installation)
	- [Usage](#usage)
	- [Roadmap](#roadmap)
		- [Authors](#authors)
	- [License](#license)

## About

Topics that will be covered include:

- Object-Oriented Design
- Software Modeling
- Design patterns
- Graphic User Interface

[Back to top](#readme-top)

## Goals

The goal of this project is to build a dashboard for the visualization of Formula 1 driver´s telemetry, based on real life data.

Formula 1 telemetry is the real‑time collection and wireless transmission of hundreds of sensor signals from an F1 car to engineers (at the pit wall and team HQ) so they can monitor, diagnose, and optimise performance and reliability during sessions and races.

For the purpose of this project we have restricted our output to the throttle and brake pressures, which are the two most important aspects of racing telemetry: they directly control the car’s two fundamental speed changes, deceleration into a corner and acceleration out of it, so small differences in their timing, magnitude, and smoothness produce the largest lap‑time gains or losses.

[Back to top](#readme-top)

## Project Structure

```text
.
├── notebooks/        # Notebooks for data exploration, prototyping, and analysis
├── src/              # Source code for the application's core logic and design pattern implementations
├── .gitignore        # Rules for excluding local, generated, and environment-specific files from Git
├── LICENSE           # License for this repository
├── README.md         # Project documentation, setup, and usage instructions
├── app.py            # Primary application entry point
├── app_dash.py       # Dashboard application entry point
└── environment.yml   # Conda environment configuration and dependencies
```

[Back to top](#readme-top)

## Getting Started

### Prerequisites

- Git
- A code editor
- Python 3.10+

### Installation

```sh
git clone https://github.com/gurovamr/Software-Engineering-and-Design-Patterns
cd Software-Engineering-and-Design-Patterns
```

[Back to top](#readme-top)

## Usage

python -m streamlit run app.py
.... 

[Back to top](#readme-top)

## Roadmap

- [x] Initialize repository and README backbone
- [x] Add data
- [x] Build a dashboard
- [x] Add local storage functionality (database).
- [x] Implement OOD principles for applicable entities

[Back to top](#readme-top)


### Authors

- **Mariiia Gurova**
	- GitHub: [@gurovamr](https://github.com/gurovamr)
- **Pia Lagler**
	- GitHub: [@Lagpi](https://github.com/Lagpi)
- **Kai Aebli**
	- GitHub: [@aeblik](https://github.com/aeblik)
- **Spyridon Margomenos**
	- Github: [@the-nerd-sloth](https://github.com/the-nerd-sloth)

[Back to top](#readme-top)

## License
Distributed under The Unlicense license.
For more information see `LICENSE`.

[Back to top](#readme-top)
