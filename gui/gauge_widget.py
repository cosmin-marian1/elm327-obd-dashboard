"""
Widget custom pentru un cadran circular (tip bord de masina), desenat direct
cu QPainter - nu exista un "GaugeWidget" nativ in Qt, il construim din arce
si linii.

Ideea de baza: valoarea curenta se mapeaza liniar din [min_value, max_value]
in unghiul acului, intre START_ANGLE si END_ANGLE (in "grade Qt", care merg
invers trigonometric si sunt in 1/16 grade pentru drawArc/drawPie).
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, QRectF, QPointF, Property, QPropertyAnimation, QEasingCurve
import math

START_ANGLE_DEG = 225
SWEEP_ANGLE_DEG = 270


class GaugeWidget(QWidget):
    def __init__(self, title: str, unit: str, min_value: float, max_value: float,
                 warning_threshold: float | None = None, parent=None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.warning_threshold = warning_threshold
        self._value = min_value
        self.setMinimumSize(180, 180)

        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(250)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_value(self) -> float:
        return self._value

    def set_value(self, value: float) -> None:
        """Setare instantanee (fara animatie) - folosita intern de QPropertyAnimation la fiecare pas."""
        self._value = max(self.min_value, min(self.max_value, value))
        self.update()

    value = Property(float, get_value, set_value)

    def animate_to(self, new_value: float) -> None:
        """API public: tranzitie lina catre noua valoare, in loc de salt brusc."""
        clamped = max(self.min_value, min(self.max_value, new_value))
        self._animation.stop()
        self._animation.setStartValue(self._value)
        self._animation.setEndValue(clamped)
        self._animation.start()

    def _value_to_angle_deg(self, value: float) -> float:
        """Mapeaza valoarea in unghiul acului (grade standard, sens trigonometric)."""
        fraction = (value - self.min_value) / (self.max_value - self.min_value)
        return START_ANGLE_DEG - fraction * SWEEP_ANGLE_DEG

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        rect = QRectF(
            (self.width() - side) / 2 + 10,
            (self.height() - side) / 2 + 10,
            side - 20,
            side - 20,
        )
        center = rect.center()
        radius = rect.width() / 2

        painter.fillRect(self.rect(), QColor("#1e1e1e"))

        self._draw_arc_track(painter, rect)
        self._draw_ticks(painter, center, radius)
        self._draw_needle(painter, center, radius)
        self._draw_labels(painter, center, radius)

        painter.end()

    def _draw_warning_zone(self, painter: QPainter, rect: QRectF) -> None:
        if self.warning_threshold is None:
            return
        start = self._value_to_angle_deg(self.warning_threshold)
        end = self._value_to_angle_deg(self.max_value)
        pen = QPen(QColor("#e74c3c"), 8)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawArc(rect, int(start * 16), int((end - start) * 16))

    def _draw_arc_track(self, painter: QPainter, rect: QRectF) -> None:
        """
        Qt masoara unghiurile la fel ca in matematica standard: 0 grade = ora 3,
        pozitiv = sens trigonometric (invers acelor de ceasornic). Asta e exact
        conventia folosita si in _value_to_angle_deg, deci startAngle = START_ANGLE_DEG
        si span-ul e negativ (mergem in sens orar pe masura ce valoarea creste).
        Unitatea nativa e 1/16 de grad, de-asta * 16.
        """
        pen = QPen(QColor("#3a3a3a"), 8)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawArc(rect, int(START_ANGLE_DEG * 16), int(-SWEEP_ANGLE_DEG * 16))

    def _draw_ticks(self, painter: QPainter, center: QPointF, radius: float) -> None:
        painter.setPen(QPen(QColor("#888888"), 2))
        num_ticks = 10
        for i in range(num_ticks + 1):
            fraction = i / num_ticks
            angle_deg = math.radians(START_ANGLE_DEG - fraction * SWEEP_ANGLE_DEG)
            outer = QPointF(center.x() + radius * math.cos(angle_deg),
                             center.y() - radius * math.sin(angle_deg))
            inner = QPointF(center.x() + (radius - 10) * math.cos(angle_deg),
                             center.y() - (radius - 10) * math.sin(angle_deg))
            painter.drawLine(inner, outer)

    def _draw_needle(self, painter: QPainter, center: QPointF, radius: float) -> None:
        angle_deg = math.radians(self._value_to_angle_deg(self._value))
        needle_len = radius - 20
        tip = QPointF(center.x() + needle_len * math.cos(angle_deg),
                       center.y() - needle_len * math.sin(angle_deg))

        needle_color = QColor("#e74c3c") if (
            self.warning_threshold is not None and self._value >= self.warning_threshold
        ) else QColor("#ecf0f1")

        painter.setPen(QPen(needle_color, 3))
        painter.drawLine(center, tip)
        painter.setBrush(QColor("#e74c3c"))
        painter.drawEllipse(center, 5, 5)

    def _draw_labels(self, painter: QPainter, center: QPointF, radius: float) -> None:
        painter.setPen(QColor("#ecf0f1"))

        value_font = QFont()
        value_font.setPointSize(14)
        value_font.setBold(True)
        painter.setFont(value_font)
        value_text = f"{self._value:.0f} {self.unit}"
        painter.drawText(
            QRectF(center.x() - radius, center.y() + radius * 0.25, radius * 2, 24),
            Qt.AlignmentFlag.AlignCenter,
            value_text,
        )

        title_font = QFont()
        title_font.setPointSize(9)
        painter.setFont(title_font)
        painter.drawText(
            QRectF(center.x() - radius, center.y() + radius * 0.55, radius * 2, 20),
            Qt.AlignmentFlag.AlignCenter,
            self.title,
        )