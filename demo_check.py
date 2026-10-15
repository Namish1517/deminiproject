
from src.storage.postgres_store import PostgresStore
from src.storage.parquet_store import ParquetStore
from src.analytics.analyze_stream import SensorAnalytics


def main():
    postgres = PostgresStore()
    parquet = ParquetStore()
    analytics = SensorAnalytics()

    try:
        postgres.initialize()

        print("=" * 55)
        print("             IoT PULSE - DEMO CHECK")
        print("=" * 55)

        print("\n1. PostgreSQL")
        print(postgres.get_stats())

        print("\n2. Latest Machine Readings")
        for reading in postgres.get_latest_readings():
            print(
                f"{reading['device_id']} | "
                f"{reading['temperature_c']}°C | "
                f"{reading['status']}"
            )

        print("\n3. Parquet Storage")
        history = parquet.load_history()
        print("Historical rows:", len(history))

        print("\n4. DuckDB Analytics")
        print(analytics.get_overview())

        print("\n5. Device Summary")
        print(analytics.get_device_summary().to_string(index=False))

        print("\nDemo check complete.")

    finally:
        postgres.close()


if __name__ == "__main__":
    main()
