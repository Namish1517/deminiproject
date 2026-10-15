
from pathlib import Path
import duckdb
import pandas as pd


class SensorAnalytics:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.parquet_file = (
            self.project_root
            / "data"
            / "warehouse"
            / "sensor_history.parquet"
        )

        self.database_file = (
            self.project_root
            / "data"
            / "warehouse"
            / "analytics.duckdb"
        )

    def _connect(self):
        return duckdb.connect(str(self.database_file))

    def get_overview(self):
        if not self.parquet_file.exists():
            return {
                "total_readings": 0,
                "fault_readings": 0,
                "devices": 0,
                "avg_temperature": 0,
                "avg_vibration": 0,
            }

        con = self._connect()

        try:
            result = con.execute("""
                SELECT
                    COUNT(*) AS total_readings,
                    COUNT(*) FILTER (WHERE status = 'FAULT')
                        AS fault_readings,
                    COUNT(DISTINCT device_id) AS devices,
                    ROUND(AVG(temperature_c), 2) AS avg_temperature,
                    ROUND(AVG(vibration_mm_s), 2) AS avg_vibration
                FROM read_parquet(?)
            """, [str(self.parquet_file)]).fetchone()

            return {
                "total_readings": result[0],
                "fault_readings": result[1],
                "devices": result[2],
                "avg_temperature": result[3] or 0,
                "avg_vibration": result[4] or 0,
            }
        finally:
            con.close()

    def get_device_summary(self):
        if not self.parquet_file.exists():
            return pd.DataFrame()

        con = self._connect()

        try:
            return con.execute("""
                SELECT
                    device_id,
                    COUNT(*) AS readings,
                    ROUND(AVG(temperature_c), 2) AS avg_temperature,
                    ROUND(MAX(temperature_c), 2) AS max_temperature,
                    ROUND(AVG(vibration_mm_s), 2) AS avg_vibration,
                    COUNT(*) FILTER (WHERE status = 'FAULT') AS faults
                FROM read_parquet(?)
                GROUP BY device_id
                ORDER BY faults DESC, avg_temperature DESC
            """, [str(self.parquet_file)]).df()
        finally:
            con.close()

    def get_hourly_trends(self):
        if not self.parquet_file.exists():
            return pd.DataFrame()

        con = self._connect()

        try:
            return con.execute("""
                SELECT
                    date_trunc('hour', timestamp) AS hour,
                    ROUND(AVG(temperature_c), 2) AS temperature,
                    ROUND(AVG(vibration_mm_s), 2) AS vibration,
                    COUNT(*) FILTER (WHERE status = 'FAULT') AS faults
                FROM read_parquet(?)
                GROUP BY hour
                ORDER BY hour
            """, [str(self.parquet_file)]).df()
        finally:
            con.close()
