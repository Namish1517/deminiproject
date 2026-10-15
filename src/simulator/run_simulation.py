
import time

from src.ingestion.mqtt_consumer import SensorIngestionPipeline
from src.simulator.sensor_simulator import MACHINES, generate_reading


def main():
    pipeline = SensorIngestionPipeline()
    pipeline.start()

    print("=" * 55)
    print("          IoT PULSE - SENSOR INGESTION")
    print("=" * 55)
    print("Simulating 8 industrial machines.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            for machine in MACHINES:
                reading = generate_reading(machine)
                pipeline.submit(reading)

                print(
                    f"{reading['device_id']} | "
                    f"Temp: {reading['temperature_c']:6.2f}°C | "
                    f"Vibration: {reading['vibration_mm_s']:5.2f} mm/s | "
                    f"Power: {reading['power_kw']:5.2f} kW | "
                    f"{reading['status']}"
                )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping simulator...")

    finally:
        pipeline.stop()

        print("\nFinal ingestion statistics:")
        for key, value in pipeline.get_stats().items():
            print(f"{key}: {value}")

        print("\nSimulation stopped.")


if __name__ == "__main__":
    main()

