"""
Interfata de nivel inalt catre ELM327: leaga conexiunea seriala de logica
de parsare si expune metode simple - connect_and_initialize(), query_pid(), read_dtcs().

Secventa de initializare AT explicata:
    ATZ    - reset complet al chip-ului
    ATE0   - opreste echo-ul
    ATL0   - opreste linefeed-urile suplimentare
    ATH0   - opreste header-ele CAN in raspuns
    ATSP0  - "set protocol auto": ELM327 detecteaza singur protocolul
"""

import time

from connection.serial_connection import ELM327Serial, SerialConnectionError
from protocol.parser import (
    parse_pid_response, parse_dtc_response,
    parse_supported_pids_response, parse_vin_response, ParseError,
)

INIT_SEQUENCE = ["ATZ", "ATE0", "ATL0", "ATH0", "ATSP0"]


class ELMInitError(Exception):
    """Adaptorul a raspuns gresit la initializare."""


class ELM327Interface:
    def __init__(self, port: str, baudrate: int = 38400):
        self._conn = ELM327Serial(port=port, baudrate=baudrate)

    def connect_and_initialize(self) -> None:
        self._conn.connect()
        for cmd in INIT_SEQUENCE:
            response = self._conn.send_command(cmd)
            if cmd == "ATZ":
                time.sleep(0.2)
            elif "OK" not in response:
                raise ELMInitError(f"{cmd} nu a fost acceptat: {response!r}")

        warmup = self._conn.send_command("0100", timeout=10.0)
        if "UNABLE TO CONNECT" in warmup.upper():
            raise ELMInitError("ECU nu raspunde. Contact pus? Adaptorul e in mufa OBD?")

    def disconnect(self) -> None:
        self._conn.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._conn.is_connected

    def query_pid(self, pid: str) -> float:
        raw = self._conn.send_command(f"01 {pid}")
        return parse_pid_response(pid, raw)

    def read_vin(self) -> str | None:
        """Citeste VIN-ul o singura data pentru fiecare conectare."""
        raw = self._conn.send_command("0902")
        try:
            return parse_vin_response(raw)
        except ParseError:
            return None

    def query_many(self, pids: list[str]) -> dict[str, float]:
        results: dict[str, float] = {}
        for pid, value in self.query_stream(pids):
            results[pid] = value
        return results

    def query_stream(self, pids: list[str]):
        """Yield-uieste fiecare PID imediat dupa ce raspunsul este decodat."""
        for pid in pids:
            try:
                yield pid, self.query_pid(pid)
            except ParseError:
                continue

    def read_dtcs(self) -> list[str]:
        raw = self._conn.send_command("03")
        try:
            return parse_dtc_response(raw)
        except ParseError:
            return []

    def clear_dtcs(self) -> None:
        """Mode 04: sterge codurile de eroare stocate si stinge MIL-ul."""
        self._conn.send_command("04")
    def query_supported_pids(self) -> set[str]:
        """
        Citeste bitmap-urile de PID-uri suportate: 0100 (PID 01-20), 0120
        (21-40), 0140 (41-60)... Ultimul bit al fiecarui bloc spune daca
        exista si urmatorul, deci inlantuim interogarile pana dam de un bit 0.
        """
        supported: set[str] = set()
        base = 0x00
        while base <= 0xE0:
            raw = self._conn.send_command(f"01 {base:02X}")
            try:
                block = parse_supported_pids_response(raw, base)
            except ParseError:
                break
            supported |= block
            if f"{base + 0x20:02X}" not in block:
                break
            base += 0x20
        return supported