"""
Punct de intrare al aplicatiei.

Rulare cu hardware real (dupa ce ai facut rfcomm bind - vezi README):
    python main.py --port /dev/rfcomm0

Rulare cu emulator, fara masina, pentru dezvoltare/testare (vezi README
pentru cum pornesti emulatorul si de unde iei calea /dev/pts/X):
    python main.py --port /dev/pts/3
"""

import sys
import argparse

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interfata OBD-II pentru modul ELM327 Bluetooth")
    parser.add_argument(
        "--port", default="/dev/rfcomm0",
        help="Portul serial al adaptorului (implicit /dev/rfcomm0)",
    )
    parser.add_argument(
        "--poll-interval", type=int, default=500,
        help="Interval de interogare a PID-urilor, in milisecunde (implicit 500)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = QApplication(sys.argv)
    window = MainWindow(port=args.port, poll_interval_ms=args.poll_interval)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
