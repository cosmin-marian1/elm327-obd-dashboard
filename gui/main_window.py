"""
Fereastra principala. Fluxul de date e strict intr-un singur sens:
PollerWorker (thread de fundal) -> semnale -> gauge-uri + grafic + logger.
Main window nu atinge niciodata portul serial direct.
"""

from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QListWidget, QMessageBox,
)

from gui.gauge_widget import GaugeWidget
from workers.poller import PollerWorker
from protocol.pids import PID_MAP, DEFAULT_POLL_ORDER
from protocol.vin import decode_vin
from storage.data_logger import CSVLogger

WARNING_THRESHOLDS: dict[str, float] = {
    "0C": 6500,
    "05": 110,
}


class MainWindow(QMainWindow):
    def __init__(self, port: str, poll_interval_ms: int = 500, history_seconds: int = 60):
        super().__init__()
        self.setWindowTitle("Interfata OBD-II - ELM327")
        self.resize(1100, 750)

        self.poller = PollerWorker(port=port, poll_interval_ms=poll_interval_ms)
        self.poller.pids_filtered.connect(self.on_pids_filtered)
        self.poller.value_ready.connect(self.on_value_ready)
        self.poller.data_ready.connect(self.on_data_ready)
        self.poller.connection_changed.connect(self.on_connection_changed)
        self.poller.error_occurred.connect(self.on_error)
        self.poller.dtcs_ready.connect(self.on_dtcs_ready)
        self.poller.vin_ready.connect(self.on_vin_ready)

        self.logger: CSVLogger | None = None
        self._hard_error = False
        self._t0: float | None = None
        self._gauge_page = 0
        self._supported_pids = set(DEFAULT_POLL_ORDER)

        max_points = max(1, int(history_seconds * 1000 / poll_interval_ms))
        self.time_history: deque[float] = deque(maxlen=max_points)
        self.rpm_history: deque[float] = deque(maxlen=max_points)

        self._build_ui()
        self.poller.start()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        header_layout = QHBoxLayout()
        self.status_label = QLabel("Se conecteaza...")
        self.status_label.setStyleSheet("font-weight: bold; padding: 4px;")
        header_layout.addWidget(self.status_label)
        self.vin_label = QLabel("VIN: se citeste...")
        self.vin_label.setStyleSheet("font-weight: bold; padding: 4px;")
        header_layout.addWidget(self.vin_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        self.vin_details_label = QLabel("")
        self.vin_details_label.setWordWrap(True)
        self.vin_details_label.setStyleSheet("padding: 0 4px 4px 4px; color: #aaaaaa;")
        main_layout.addWidget(self.vin_details_label)

        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout, stretch=3)

        content_layout.addLayout(self._build_gauges_grid(), stretch=3)
        content_layout.addLayout(self._build_side_panel(), stretch=1)

        main_layout.addWidget(self._build_plot(), stretch=2)

    def _build_gauges_grid(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        self.gauge_grid = QGridLayout()
        self.gauges: dict[str, GaugeWidget] = {}
        columns = 4
        for pid in DEFAULT_POLL_ORDER:
            pid_def = PID_MAP[pid]
            gauge = GaugeWidget(
                title=pid_def.name,
                unit=pid_def.unit,
                min_value=pid_def.value_range[0],
                max_value=pid_def.value_range[1],
                warning_threshold=WARNING_THRESHOLDS.get(pid),
            )
            self.gauges[pid] = gauge
        layout.addLayout(self.gauge_grid)

        navigation = QHBoxLayout()
        self.previous_page_btn = QPushButton("Pagina anterioara")
        self.previous_page_btn.clicked.connect(self._previous_gauge_page)
        navigation.addWidget(self.previous_page_btn)
        self.gauge_page_label = QLabel()
        self.gauge_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        navigation.addWidget(self.gauge_page_label, stretch=1)
        self.next_page_btn = QPushButton("Pagina urmatoare")
        self.next_page_btn.clicked.connect(self._next_gauge_page)
        navigation.addWidget(self.next_page_btn)
        layout.addLayout(navigation)
        self._update_gauge_page()
        return layout

    def _build_side_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Coduri de eroare (DTC)"))
        self.dtc_list = QListWidget()
        layout.addWidget(self.dtc_list)

        btn_row = QHBoxLayout()
        self.read_btn = QPushButton("Citeste DTC")
        self.read_btn.clicked.connect(self.poller.request_read_dtcs)
        self.clear_btn = QPushButton("Sterge DTC")
        self.clear_btn.clicked.connect(self._on_clear_dtcs_clicked)
        btn_row.addWidget(self.read_btn)
        btn_row.addWidget(self.clear_btn)
        layout.addLayout(btn_row)

        self.log_btn = QPushButton("Porneste logging CSV")
        self.log_btn.setCheckable(True)
        self.log_btn.toggled.connect(self.on_log_toggled)
        layout.addWidget(self.log_btn)

        layout.addStretch()
        return layout

    def _build_plot(self) -> pg.PlotWidget:
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#1e1e1e")
        self.plot_widget.setLabel("left", "RPM")
        self.plot_widget.setLabel("bottom", "Timp (s)")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setAntialiasing(True)
        self.rpm_curve = self.plot_widget.plot(pen=pg.mkPen("#e74c3c", width=2))
        return self.plot_widget

    def on_pids_filtered(self, poll_list: list[str]) -> None:
        """Ascunde gauge-urile PID-urilor nesuportate - un gauge blocat pe 0%
        ar parea o citire reala (ex: 'rezervor gol'), ceea ce e misleading."""
        self._supported_pids = set(poll_list)
        self._gauge_page = 0
        self._update_gauge_page()

    def _update_gauge_page(self) -> None:
        visible_pids = [
            pid for pid in DEFAULT_POLL_ORDER if pid in self._supported_pids
        ]
        page_size = 8
        page_count = max(1, (len(visible_pids) + page_size - 1) // page_size)
        self._gauge_page = min(self._gauge_page, page_count - 1)
        page_pids = visible_pids[
            self._gauge_page * page_size:(self._gauge_page + 1) * page_size
        ]
        for gauge in self.gauges.values():
            self.gauge_grid.removeWidget(gauge)
            gauge.setVisible(False)
        for index, pid in enumerate(page_pids):
            gauge = self.gauges[pid]
            self.gauge_grid.addWidget(gauge, index // 4, index % 4)
            gauge.setVisible(True)
        self.gauge_page_label.setText(f"Pagina {self._gauge_page + 1} / {page_count}")
        self.previous_page_btn.setEnabled(self._gauge_page > 0)
        self.next_page_btn.setEnabled(self._gauge_page < page_count - 1)

    def _previous_gauge_page(self) -> None:
        self._gauge_page -= 1
        self._update_gauge_page()

    def _next_gauge_page(self) -> None:
        self._gauge_page += 1
        self._update_gauge_page()

    def on_data_ready(self, timestamp: float, values: dict[str, float]) -> None:
        if self.logger is not None:
            self.logger.log_row(values)

    def on_value_ready(self, timestamp: float, pid: str, value: float) -> None:
        if pid in self.gauges:
            self.gauges[pid].animate_to(value)

        if pid == "0C":
            if self._t0 is None:
                self._t0 = timestamp
            self.time_history.append(timestamp - self._t0)
            self.rpm_history.append(value)
            self.rpm_curve.setData(list(self.time_history), list(self.rpm_history))

    def on_connection_changed(self, connected: bool) -> None:
        if connected:
            self._hard_error = False
        elif self._hard_error:
            self.read_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
            return
        self.read_btn.setEnabled(connected)
        self.clear_btn.setEnabled(connected)
        self.status_label.setText("Conectat" if connected else "Deconectat")
        self.status_label.setStyleSheet(
            f"font-weight: bold; padding: 4px; color: {'#2ecc71' if connected else '#e74c3c'};"
        )

    def on_error(self, message: str) -> None:
        self._hard_error = True
        self.status_label.setText(f"Eroare: {message}")
        self.status_label.setStyleSheet("font-weight: bold; padding: 4px; color: #e74c3c;")

    def on_dtcs_ready(self, codes: list[str]) -> None:
        self.dtc_list.clear()
        self.dtc_list.addItems(codes if codes else ["Niciun cod de eroare stocat"])

    def on_vin_ready(self, vin: str) -> None:
        self.vin_label.setText(f"VIN: {vin}")
        if vin == "indisponibil":
            self.vin_details_label.clear()
            return
        details = decode_vin(vin)
        self.vin_details_label.setText(
            f"Producator: {details['producator']} | Tara: {details['tara']} | "
            f"An model: {details['an_model']} | Fabrica: {details['fabrica']} | "
            f"Serie: {details['serie']} | Model: {details['model']}"
        )

    def _on_clear_dtcs_clicked(self) -> None:
        """Mode 04 sterge coduri, stinge MIL si reseteaza monitorii de emisii
        (masina pica inspectia pana se refac) - de aceea cerem confirmare."""
        reply = QMessageBox.question(
            self, "Confirmare",
            "Mode 04 sterge codurile de eroare, stinge MIL (check-engine) si "
            "reseteaza monitorii de emisii. Continui?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.poller.request_clear_dtcs()

    def on_log_toggled(self, checked: bool) -> None:
        if checked:
            self.logger = CSVLogger()
            self.log_btn.setText("Opreste logging CSV")
        else:
            logger = self.logger
            self.logger = None
            if logger is not None:
                saved_path = logger.path
                logger.close()
                QMessageBox.information(
                    self, "Logging oprit", f"Fisier salvat la:\n{saved_path}"
                )
            self.log_btn.setText("Porneste logging CSV")

    def closeEvent(self, event) -> None:
        self.poller.stop()
        if self.logger is not None:
            self.logger.close()
        super().closeEvent(event)