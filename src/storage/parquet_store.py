
from pathlib import Path
import pandas as pd


class ParquetStore:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.processed_dir = self.project_root / "data" / "processed"
        self.warehouse_dir = self.project_root / "data" / "warehouse"

        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.warehouse_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.warehouse_dir / "sensor_history.parquet"

    def save_batch(self, readings):
        if not readings:
            return 0

        new_df = pd.DataFrame(readings)

        if self.history_file.exists():
            old_df = pd.read_parquet(self.history_file)
            new_df = pd.concat([old_df, new_df], ignore_index=True)

        new_df["timestamp"] = pd.to_datetime(
            new_df["timestamp"], utc=True
        )

        new_df.to_parquet(self.history_file, index=False)

        return len(readings)

    def load_history(self):
        if not self.history_file.exists():
            return pd.DataFrame()

        return pd.read_parquet(self.history_file)

    def export_csv(self):
        df = self.load_history()
        output = self.processed_dir / "sensor_history.csv"
        df.to_csv(output, index=False)
        return output

