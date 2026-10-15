
import json
import random
import time
from datetime import datetime, timezone

MACHINES = [f"MACHINE_{i:03d}" for i in range(1, 9)]


def generate_reading(device_id: str) -> dict:
    """Generate one simulated industrial IoT sensor reading."""

    temperature = round(random.uniform(55, 85), 2)
    humidity = round(random.uniform(30, 70), 2)
    vibration = round(random.uniform(0.2, 4.0), 2)
    power = round(random.uniform(5, 25), 2)

    # Occasionally simulate an abnormal machine condition.
    if random.random() < 0.08:
        fault_type = random.choice(["overheating", "vibration", "power"])

        if fault_type == "overheating":
            temperature = round(random.uniform(95, 115), 2)
        elif fault_type == "vibration":
            vibration = round(random.uniform(8, 15), 2)
        else:
            power = round(random.uniform(35, 50), 2)

    status = (
        "FAULT"
        if temperature > 90 or vibration > 7 or power > 30
        else "NORMAL"
    )

    return {
        "device_id": device_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "vibration_mm_s": vibration,
        "power_kw": power,
        "status": status,
    }


def main():
    print("IoT Pulse Sensor Simulator")
    print("Generating readings for 8 machines. Press Ctrl+C to stop.\n")

    try:
        while True:
            for machine in MACHINES:
                reading = generate_reading(machine)
                print(json.dumps(reading))
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nSensor simulation stopped.")


if __name__ == "__main__":
    main()

