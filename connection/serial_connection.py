"""
Strat de conexiune seriala catre modulul ELM327.

Pe Linux, dupa pairing, portul apare la /dev/rfcomm0 (vezi README).
Pe Windows, pairing-ul Bluetooth creaza un port COM "outgoing" pentru
dispozitiv - ala e portul pe care il dai la --port (ex: COM11).
"""

import time
import serial


class SerialConnectionError(Exception):
    """Nu s-a putut deschide/citi/scrie pe portul serial."""


class ELM327Serial:
    def __init__(self, port: str, baudrate: int = 38400, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: serial.Serial | None = None

    def connect(self) -> None:
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=1.0,
            )
            time.sleep(1.0)
        except serial.SerialException as exc:
            raise SerialConnectionError(f"Nu pot deschide {self.port}: {exc}") from exc

    def disconnect(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def send_command(self, command: str, timeout: float | None = None) -> str:
        """
        Trimite o comanda si citeste pana la promptul '>'.
        Parametrul timeout suprascrie deadline-ul implicit (ex: cautarea de
        protocol dupa ATSP0 poate dura 3-10s pe masini non-CAN).
        """
        if not self.is_connected:
            raise SerialConnectionError("Portul serial nu este deschis")

        try:
            self._serial.reset_input_buffer()
            self._serial.write((command + "\r").encode("ascii"))
            effective = self.timeout if timeout is None else timeout
            return self._read_until_prompt(effective)
        except serial.SerialException as exc:
            raise SerialConnectionError(f"Eroare de comunicare pe {self.port}: {exc}") from exc

    def _read_until_prompt(self, timeout: float) -> str:
        buffer = b""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            chunk = self._serial.read(64)
            if chunk:
                buffer += chunk
                if b">" in buffer:
                    break
            else:
                time.sleep(0.02)
        return buffer.decode("ascii", errors="ignore")