
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class PostgresStore:
    def __init__(self):
        connection_url = URL.create(
            drivername="postgresql+psycopg",
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "iot_pulse"),
        )

        self.engine = create_engine(connection_url, pool_pre_ping=True)

    def initialize(self):
        statements = [
            """
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                location TEXT NOT NULL,
                registered_at TIMESTAMPTZ DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id BIGSERIAL PRIMARY KEY,
                device_id TEXT NOT NULL REFERENCES devices(device_id),
                timestamp TIMESTAMPTZ NOT NULL,
                temperature_c DOUBLE PRECISION NOT NULL,
                humidity_pct DOUBLE PRECISION NOT NULL,
                vibration_mm_s DOUBLE PRECISION NOT NULL,
                power_kw DOUBLE PRECISION NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('NORMAL', 'FAULT'))
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_sensor_device_time
            ON sensor_readings(device_id, timestamp DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id BIGSERIAL PRIMARY KEY,
                device_id TEXT NOT NULL REFERENCES devices(device_id),
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                temperature_c DOUBLE PRECISION,
                vibration_mm_s DOUBLE PRECISION,
                power_kw DOUBLE PRECISION,
                acknowledged BOOLEAN DEFAULT FALSE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS quarantined_records (
                id BIGSERIAL PRIMARY KEY,
                received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                record JSONB NOT NULL,
                reason TEXT NOT NULL
            )
            """,
        ]

        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

            for i in range(1, 9):
                device_id = f"MACHINE_{i:03d}"
                connection.execute(
                    text("""
                        INSERT INTO devices (device_id, device_name, location)
                        VALUES (:id, :name, :location)
                        ON CONFLICT (device_id) DO NOTHING
                    """),
                    {
                        "id": device_id,
                        "name": f"Industrial Machine {i:03d}",
                        "location": f"Production Zone {(i - 1) // 2 + 1}",
                    },
                )

    def save_reading(self, reading):
        with self.engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO sensor_readings (
                        device_id, timestamp, temperature_c,
                        humidity_pct, vibration_mm_s, power_kw, status
                    )
                    VALUES (
                        :device_id, :timestamp, :temperature_c,
                        :humidity_pct, :vibration_mm_s, :power_kw, :status
                    )
                """),
                reading,
            )

            if reading["status"] == "FAULT":
                messages = []

                if reading["temperature_c"] > 90:
                    messages.append("High temperature")
                if reading["vibration_mm_s"] > 7:
                    messages.append("Excessive vibration")
                if reading["power_kw"] > 30:
                    messages.append("Abnormal power consumption")

                connection.execute(
                    text("""
                        INSERT INTO alerts (
                            device_id, timestamp, severity, message,
                            temperature_c, vibration_mm_s, power_kw
                        )
                        VALUES (
                            :device_id, :timestamp, :severity, :message,
                            :temperature_c, :vibration_mm_s, :power_kw
                        )
                    """),
                    {
                        **reading,
                        "severity": (
                            "CRITICAL"
                            if reading["temperature_c"] > 100
                            or reading["vibration_mm_s"] > 10
                            else "HIGH"
                        ),
                        "message": ", ".join(messages) or "Machine fault detected",
                    },
                )

    def save_quarantined_record(self, record, reason):
        with self.engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO quarantined_records (record, reason)
                    VALUES (CAST(:record AS JSONB), :reason)
                """),
                {
                    "record": json.dumps(record, default=str),
                    "reason": reason,
                },
            )

    def get_latest_readings(self):
        with self.engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT DISTINCT ON (r.device_id)
                    r.device_id, r.timestamp, r.temperature_c,
                    r.humidity_pct, r.vibration_mm_s, r.power_kw, r.status,
                    d.device_name, d.location
                FROM sensor_readings r
                JOIN devices d USING (device_id)
                ORDER BY r.device_id, r.timestamp DESC, r.id DESC
            """)).mappings().all()

        return [dict(row) for row in rows]

    def get_alerts(self, limit=100):
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("""
                    SELECT id, device_id, timestamp, severity,
                           message, acknowledged
                    FROM alerts
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).mappings().all()

        return [dict(row) for row in rows]

    def get_readings(self, limit=2000):
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("""
                    SELECT device_id, timestamp, temperature_c,
                           humidity_pct, vibration_mm_s, power_kw, status
                    FROM sensor_readings
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).mappings().all()

        return [dict(row) for row in rows]

    def get_stats(self):
        with self.engine.connect() as connection:
            return dict(connection.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM devices) AS devices,
                    (SELECT COUNT(*) FROM sensor_readings) AS readings,
                    (SELECT COUNT(*) FROM alerts) AS alerts,
                    (SELECT COUNT(*) FROM quarantined_records) AS quarantined
            """)).mappings().one())

    def close(self):
        self.engine.dispose()
