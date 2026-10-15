
import queue
import threading

from src.ingestion.validator import validate_reading
from src.storage.postgres_store import PostgresStore
from src.storage.parquet_store import ParquetStore


class SensorIngestionPipeline:
    def __init__(self, store=None):
        self.message_queue = queue.Queue()
        self.running = False
        self.thread = None

        self.store = store or PostgresStore()
        self.owns_store = store is None
        self.parquet = ParquetStore()

        self.processed_count = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.storage_errors = 0

        self.latest_readings = {}
        self.invalid_records = []
        self.valid_batch = []

        self._lock = threading.Lock()
        self.batch_size = 20

    def submit(self, reading):
        self.message_queue.put(reading)

    def _flush_batch(self):
        if not self.valid_batch:
            return

        batch = self.valid_batch
        self.valid_batch = []

        try:
            self.parquet.save_batch(batch)
        except Exception as exc:
            with self._lock:
                self.storage_errors += 1
            print(f"Parquet storage error: {exc}")

    def _consume(self):
        while self.running or not self.message_queue.empty():
            try:
                reading = self.message_queue.get(timeout=0.5)
            except queue.Empty:
                self._flush_batch()
                continue

            try:
                with self._lock:
                    self.processed_count += 1

                is_valid, reason = validate_reading(reading)

                if not is_valid:
                    self.store.save_quarantined_record(reading, reason)

                    with self._lock:
                        self.invalid_count += 1
                        self.invalid_records.append({
                            "record": reading,
                            "reason": reason,
                        })
                    continue

                self.store.save_reading(reading)

                with self._lock:
                    self.valid_count += 1
                    self.latest_readings[reading["device_id"]] = reading
                    self.valid_batch.append(reading)

                if len(self.valid_batch) >= self.batch_size:
                    self._flush_batch()

            except Exception as exc:
                with self._lock:
                    self.storage_errors += 1
                print(f"Ingestion/storage error: {exc}")

            finally:
                self.message_queue.task_done()

        self._flush_batch()

    def start(self):
        if self.running:
            return

        self.store.initialize()
        self.running = True

        self.thread = threading.Thread(
            target=self._consume,
            daemon=True,
        )
        self.thread.start()

    def stop(self):
        self.running = False

        if self.thread:
            self.thread.join(timeout=10)

        if self.owns_store:
            self.store.close()

    def get_stats(self):
        with self._lock:
            return {
                "processed": self.processed_count,
                "valid": self.valid_count,
                "invalid": self.invalid_count,
                "storage_errors": self.storage_errors,
                "devices_seen": len(self.latest_readings),
                "queue_size": self.message_queue.qsize(),
            }
