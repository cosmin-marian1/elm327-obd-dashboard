"""
Worker care ruleaza pe un QThread separat si interogheaza periodic ELM327.

I/O-ul serial se face doar aici; GUI-ul primeste date exclusiv prin semnale.
In plus: la conectare se descopera ce PID-uri suporta ECU-ul si se interogheaza
doar acelea (un ECU care nu raporteaza un PID ar raspunde "NO DATA" la fiecare
cicl - timp pierdut + gauge blocat pe valoarea de start).
"""

import time

from PySide6.QtCore import QThread, Signal

from protocol.elm327 import ELM327Interface, ELMInitError
from protocol.parser import ParseError
from protocol.pids import DEFAULT_POLL_ORDER
from connection.serial_connection import SerialConnectionError


class PollerWorker(QThread):
    data_ready = Signal(float, dict)
    value_ready = Signal(float, str, float)
    pids_filtered = Signal(list)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)
    dtcs_ready = Signal(list)
    vin_ready = Signal(str)

    def __init__(self, port: str, poll_interval_ms: int = 500, parent=None):
        super().__init__(parent)
        self.port = port
        self.poll_interval_ms = poll_interval_ms
        self._elm: ELM327Interface | None = None
        self._running = False
        self._empty_cycles = 0
        self._poll_list: list[str] = list(DEFAULT_POLL_ORDER)
        self._dtc_read_requested = False
        self._dtc_clear_requested = False

    def run(self) -> None:
        self._running = True
        self._empty_cycles = 0
        self._elm = ELM327Interface(port=self.port)

        try:
            self._elm.connect_and_initialize()
            self._read_vin()
            self._prepare_after_connect()
            self.connection_changed.emit(True)
        except (SerialConnectionError, ELMInitError) as exc:
            self.error_occurred.emit(str(exc))
            self.connection_changed.emit(False)
            return

        while self._running:
            try:
                if self._dtc_read_requested:
                    self._dtc_read_requested = False
                    self.dtcs_ready.emit(self._elm.read_dtcs())
                elif self._dtc_clear_requested:
                    self._dtc_clear_requested = False
                    self._elm.clear_dtcs()
                else:
                    values = {}
                    for pid, value in self._elm.query_stream(self._poll_list):
                        values[pid] = value
                        self.value_ready.emit(time.time(), pid, value)
                    if values:
                        self._empty_cycles = 0
                        self.data_ready.emit(time.time(), values)
                    else:
                        self._empty_cycles += 1
                        if self._empty_cycles >= 3:
                            raise SerialConnectionError("adaptorul nu mai raspunde")
                self._interruptible_sleep(self.poll_interval_ms)

            except SerialConnectionError as exc:
                self.error_occurred.emit(f"Conexiune pierduta: {exc}")
                self.connection_changed.emit(False)
                if not self._reconnect():
                    break
                self._empty_cycles = 0

        self._elm.disconnect()
        self.connection_changed.emit(False)

    def _prepare_after_connect(self) -> None:
        """Descopera PID-urile suportate si anunta GUI-ul inainte de polling."""
        try:
            supported = self._elm.query_supported_pids()
        except (SerialConnectionError, ParseError):
            supported = set()
        if supported:
            self._poll_list = [p for p in DEFAULT_POLL_ORDER if p in supported]
        else:
            self._poll_list = list(DEFAULT_POLL_ORDER)
        self.pids_filtered.emit(list(self._poll_list))

    def _reconnect(self) -> bool:
        """Reincearca conectarea cu pauze crescatoare: 1s, 2s, 4s... max 30s."""
        self._elm.disconnect()
        backoff_ms = 1000
        while self._running:
            self._interruptible_sleep(backoff_ms)
            if not self._running:
                return False
            try:
                self._elm.connect_and_initialize()
                self._read_vin()
                self._prepare_after_connect()
                self.connection_changed.emit(True)
                return True
            except (SerialConnectionError, ELMInitError):
                backoff_ms = min(backoff_ms * 2, 30_000)
        return False

    def _read_vin(self) -> None:
        vin = self._elm.read_vin()
        self.vin_ready.emit(vin or "indisponibil")

    def _interruptible_sleep(self, total_ms: int) -> None:
        slept = 0
        while slept < total_ms and self._running:
            chunk = min(50, total_ms - slept)
            self.msleep(chunk)
            slept += chunk

    def stop(self) -> None:
        self._running = False
        self.wait()

    def request_read_dtcs(self) -> None:
        self._dtc_read_requested = True

    def request_clear_dtcs(self) -> None:
        self._dtc_clear_requested = True