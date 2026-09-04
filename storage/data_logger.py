"""
Logging simplu in CSV al datelor citite de la ELM327, cu timestamp pe fiecare
rand. Fiecare sesiune de logging genereaza un fisier nou, numit dupa data si
ora de start, ca sa nu suprascrii accidental un log anterior.
"""

import csv
import time
from pathlib import Path

from protocol.pids import PID_MAP, DEFAULT_POLL_ORDER
from datetime import datetime

class CSVLogger:
    def __init__(self):
        output_dir = Path(__file__).resolve().parents[1] / "logs"
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"obd_log_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        self.path = Path(output_dir) / filename

        self._file = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        header = ["timestamp"] + [PID_MAP[pid].name for pid in DEFAULT_POLL_ORDER]
        self._writer.writerow(header)

    def log_row(self, values: dict[str, float]) -> None:
        row = [datetime.now().isoformat(timespec="milliseconds")]
        for pid in DEFAULT_POLL_ORDER:
            row.append(values.get(pid, ""))
        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()
