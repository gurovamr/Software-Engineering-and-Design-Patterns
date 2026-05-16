"""
pytest configuration file

This file is automatically loaded by pytest before running any tests.
It adds the project root to sys.path so tests can import project modules.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
