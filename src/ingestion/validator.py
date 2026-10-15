
from datetime import datetime


REQUIRED_FIELDS = {
    "device_id",
    "timestamp",
    "temperature_c",
    "humidity_pct",
    "vibration_mm_s",
    "power_kw",
    "status",
}


def validate_reading(reading: dict) -> tuple[bool, str]:
    """Validate one sensor reading."""

    missing_fields = REQUIRED_FIELDS - reading.keys()

    if missing_fields:
        return False, f"Missing fields: {', '.join(sorted(missing_fields))}"

    if not isinstance(reading["device_id"], str) or not reading["device_id"]:
        return False, "Invalid device_id"

    try:
        datetime.fromisoformat(reading["timestamp"].replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return False, "Invalid timestamp"

    numeric_fields = [
        "temperature_c",
        "humidity_pct",
        "vibration_mm_s",
        "power_kw",
    ]

    for field in numeric_fields:
        value = reading[field]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, f"{field} must be numeric"

        if not float("-inf") < value < float("inf"):
            return False, f"{field} must be finite"

    if not 0 <= reading["humidity_pct"] <= 100:
        return False, "Humidity must be between 0 and 100"

    if reading["vibration_mm_s"] < 0 or reading["power_kw"] < 0:
        return False, "Vibration and power cannot be negative"

    if reading["status"] not in {"NORMAL", "FAULT"}:
        return False, "Invalid status"

    return True, "Valid reading"

