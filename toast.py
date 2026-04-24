from PyQt5.QtWidgets import QLabel, QApplication
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor


class Toast(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background: rgba(30, 30, 50, 220);
                color: rgba(160, 220, 160, 1);
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 18px;
                padding: 8px 20px;
                font-size: 13px;
                font-family: 'Segoe UI';
            }
        """)
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)

    def show_message(self, msg="Message copied", duration=1800):
        self.setText(msg)
        self.adjustSize()
        self._position()
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self._timer.start(duration)

    def _position(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 60
        self.move(x, y)

    def _fade_out(self):
        self._anim.stop()
        self._anim.setDuration(400)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.hide)
        self._anim.start()


# singleton per-process
_toast = None

def show_toast(msg="Message copied"):
    global _toast
    if _toast is None:
        _toast = Toast()
    _toast.show_message(msg)
