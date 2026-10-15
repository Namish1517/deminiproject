
from src.storage.postgres_store import PostgresStore

store = PostgresStore()

try:
    store.initialize()

    print("PostgreSQL tables initialized!")
    print("Database statistics:", store.get_stats())

    sample = {
        "device_id": "MACHINE_001",
        "timestamp": "2026-10-15T12:00:00+00:00",
        "temperature_c": 72.5,
        "humidity_pct": 45.0,
        "vibration_mm_s": 1.2,
        "power_kw": 14.5,
        "status": "NORMAL",
    }

    store.save_reading(sample)
    print("Sample reading inserted successfully.")

finally:
    store.close()
