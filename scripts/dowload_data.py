import kagglehub
from pathlib import Path

data_dir = Path(__file__).resolve().parent.parent / "data"
data_dir.mkdir(exist_ok=True)

# Download latest version
kagglehub.dataset_download("jtrotman/formula-1-race-data", output_dir=data_dir, force_download=True)

