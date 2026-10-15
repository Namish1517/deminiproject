
from src.ingestion.validator import validate_reading
from src.ingestion.mqtt_consumer import SensorIngestionPipeline


sample_reading = {
    "device_id": "MACHINE_001",
    "timestamp": "2026-10-15T15:00:00+00:00",
    "temperature_c": 72.4,
    "humidity_pct": 46.2,
    "vibration_mm_s": 1.45,
    "power_kw": 14.8,
    "status": "NORMAL",
}


def main():
    valid, message = validate_reading(sample_reading)
    print("Valid record:", valid, "-", message)

    invalid_reading = sample_reading.copy()
    invalid_reading["humidity_pct"] = 150

    valid, message = validate_reading(invalid_reading)
    print("Invalid record:", valid, "-", message)

    pipeline = SensorIngestionPipeline()
    pipeline.start()

    pipeline.submit(sample_reading)
    pipeline.submit(invalid_reading)

    pipeline.message_queue.join()
    pipeline.stop()

    print("\nPipeline statistics:")
    print(pipeline.get_stats())


if __name__ == "__main__":
    main()
