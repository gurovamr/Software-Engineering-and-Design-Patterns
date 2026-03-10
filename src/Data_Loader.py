import pandas as pd
from pathlib import Path

class DataLoader:
    """
    A class to load and merge CSV files from a specified folder.
    Attributes:
        folder_path (Path): The path to the folder containing the CSV files.
    Methods:
        get_csv_files(): Returns a list of all CSV files in the specified folder.
        read_csv(file_path): Reads a CSV file and returns a DataFrame.
        merge_files(): Reads all CSV files and merges them into a single DataFrame.
        load(): Loads and returns the merged DataFrame.
    """

    def __init__(self, folder_path):
        self.folder_path = Path(folder_path)

    def get_csv_files(self):
        return list(self.folder_path.glob("*.csv"))

    def read_csv(self, file_path):
        return pd.read_csv(file_path)

    def merge_files(self):
        dfs = []
        for file in self.get_csv_files():
            dfs.append(self.read_csv(file))

        return pd.concat(dfs, ignore_index=True)

    def load(self):
        return self.merge_files()