from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QCursor
import database as db
import groq_client
from styles import get_stylesheet

# ── constants ────────────────────────────────────────────────────────────────
W            = 340
BTN_D        = 45
BTN_Y        = 9
BTN_X        = 5
CAP_MIN_H    = BTN_D + BTN_Y * 2
INPUT_MIN_H  = BTN_D
INPUT_MAX_H  = 120
INPUT_X      = BTN_D + BTN_X + 4
INPUT_W      = W - BTN_D * 2 - BTN_X * 2 - 8
BODY_W       = W - 30
MAX_BODY_H   = 420
EXPAND_BTN   = 28

CARD_BG  = QColor(18, 18, 30, 235)
CARD_EDGE= QColor(255, 255, 255, 22)
CAP_BG   = QColor(28, 28, 46, 250)
CAP_EDGE = QColor(255, 255, 255, 32)


# ── worker ────────────────────────────────────────────────────────────────────
class GroqWorker(QThread):
    response_ready = pyqtSignal(str)
    def __init__(self, messages):
        super().__init__()
        self.messages = messages
    def run(self):
        self.response_ready.emit(groq_client.get_response(self.messages))


# ── bubble with copy button (same row) ───────────────────────────────────────
class MessageBubble(QWidget):
    def __init__(self, text, is_user, theme="dark"):
        super().__init__()
        self._text = text
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        label.setMaximumWidth(BODY_W - 40)

        if theme == "light":
            user_css = ("background:rgba(210,212,255,0.9);border:1px solid rgba(0,0,0,0.15);"
                        "border-radius:10px;padding:7px 11px;color:#000000;font-size:12px;")
            bot_css  = ("background:rgba(255,255,255,0.95);border:1px solid rgba(0,0,0,0.15);"
                        "border-radius:10px;padding:7px 11px;color:#000000;font-size:12px;")
            copy_color = "rgba(0,0,0,0.3)"
            copy_hover = "rgba(0,0,0,0.7)"
        else:
            user_css = ("background:rgba(99,102,241,0.22);border:1px solid rgba(99,102,241,0.35);"
                        "border-radius:10px;padding:7px 11px;color:#dde;font-size:12px;")
            bot_css  = ("background:rgba(40,40,60,0.7);border:1px solid rgba(255,255,255,0.08);"
                        "border-radius:10px;padding:7px 11px;color:#d0d0d0;font-size:12px;")
            copy_color = "rgba(255,255,255,0.28)"
            copy_hover = "rgba(255,255,255,0.85)"

        label.setStyleSheet(user_css if is_user else bot_css)

        copy_btn = QPushButton("⧉")
        copy_btn.setFixedSize(20, 20)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setToolTip("Copy")
        copy_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                          color:{copy_color}; font-size:12px; }}
            QPushButton:hover {{ color:{copy_hover}; }}
        """)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self._text))
        copy_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        if is_user:
            row.addStretch()
            row.addWidget(label)
            row.addWidget(copy_btn)
        else:
            row.addWidget(copy_btn)
            row.addWidget(label)
            row.addStretch()


# ── popup ─────────────────────────────────────────────────────────────────────
class PopupWindow(QWidget):
    open_main = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.conv_id  = None
        self._card_bg   = CARD_BG
        self._card_edge = CARD_EDGE
        self._cap_bg    = CAP_BG
        self._cap_edge  = CAP_EDGE
        self._theme   = "dark"
        self.drag_pos = None
        self._body_h  = 0
        self._input_h = INPUT_MIN_H
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui()
        self._resize()
        self.apply_theme(db.get_theme())
        # close when clicking outside if input+chat empty
        QApplication.instance().installEventFilter(self)

    def apply_theme(self, theme):
        if theme == "light":
            self._card_bg   = QColor(240, 242, 248, 245)
            self._card_edge = QColor(0, 0, 0, 46)
            self._cap_bg    = QColor(255, 255, 255, 245)
            self._cap_edge  = QColor(0, 0, 0, 55)
            txt_color = "#000000"
            self._theme = "light"
            icon_color  = "rgba(0,0,0,0.45)"
            icon_hover_close = "rgba(200,0,0,0.9)"
            icon_hover_expand = "rgba(99,102,241,1)"
        else:
            self._card_bg   = CARD_BG
            self._card_edge = CARD_EDGE
            self._cap_bg    = CAP_BG
            self._cap_edge  = CAP_EDGE
            txt_color = "white"
            self._theme = "dark"
            icon_color  = "rgba(255,255,255,0.25)"
            icon_hover_close = "rgba(255,80,80,1)"
            icon_hover_expand = "rgba(99,102,241,1)"
        self.input_bar.setStyleSheet(f"""
            QTextEdit {{ background:transparent; border:none;
                        color:{txt_color}; font-size:13px;
                        font-family:'Segoe UI'; padding:4px 8px; }}
        """)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                          color:{icon_color}; font-size:13px; }}
            QPushButton:hover {{ color:{icon_hover_close}; }}
        """)
        self.expand_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                          color:{icon_color}; font-size:14px; }}
            QPushButton:hover {{ color:{icon_hover_expand}; }}
        """)
        self.update()

    def _cap_h(self):
        extra = max(0, self._input_h - INPUT_MIN_H)
        return CAP_MIN_H + extra

    # ── paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cap_h = self._cap_h()
        r = min(cap_h // 2, 32)

        cap = QPainterPath()
        cap.addRoundedRect(0, 0, W, cap_h, r, r)
        p.setPen(self._cap_edge)
        p.setBrush(self._cap_bg)
        p.drawPath(cap)

        if self._body_h > 0:
            body = QPainterPath()
            body.addRoundedRect(15, cap_h - 12, BODY_W, self._body_h + 12, 18, 18)
            p.setPen(self._card_edge)
            p.setBrush(self._card_bg)
            p.drawPath(body)
        p.end()

    # ── build ui ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.plus_btn = QPushButton("+", self)
        self.plus_btn.setFixedSize(BTN_D, BTN_D)
        self.plus_btn.move(BTN_X, BTN_Y)
        self.plus_btn.setCursor(Qt.PointingHandCursor)
        self.plus_btn.clicked.connect(self._new_conversation)
        self.plus_btn.setStyleSheet(self._btn_css(False))

        self.send_btn = QPushButton("➤", self)
        self.send_btn.setFixedSize(BTN_D, BTN_D)
        self.send_btn.move(W - BTN_D - BTN_X, BTN_Y)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._send)
        self.send_btn.setStyleSheet(self._btn_css(True))

        self.input_bar = QTextEdit(self)
        self.input_bar.setPlaceholderText("Ask anything...")
        self.input_bar.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_bar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_bar.setStyleSheet("""
            QTextEdit {
                background: transparent; border: none;
                color: white; font-size: 13px;
                font-family: 'Segoe UI'; padding: 4px 8px;
            }
        """)
        self.input_bar.textChanged.connect(self._on_input_changed)
        self.input_bar.installEventFilter(self)
        self._reposition_input()

        self.card = QWidget(self)
        self.card.setStyleSheet("background: transparent;")
        self.card.hide()

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(10, 14, 10, 6)
        card_layout.setSpacing(4)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: transparent; width: 3px; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius:1px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setSpacing(6)
        self.chat_layout.setContentsMargins(2, 2, 2, 2)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_widget)
        card_layout.addWidget(self.scroll, 1)

        # bottom row: close ✕ left, expand ↗ right
        exp_row = QHBoxLayout()
        exp_row.setContentsMargins(0, 0, 0, 0)
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(EXPAND_BTN, EXPAND_BTN)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton { background:transparent; border:none;
                          color:rgba(255,255,255,0.25); font-size:13px; }
            QPushButton:hover { color:rgba(255,80,80,1); }
        """)
        self.close_btn.clicked.connect(self.hide)
        self.expand_btn = QPushButton("↗")
        self.expand_btn.setFixedSize(EXPAND_BTN, EXPAND_BTN)
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setStyleSheet("""
            QPushButton { background:transparent; border:none;
                          color:rgba(255,255,255,0.25); font-size:14px; }
            QPushButton:hover { color:rgba(99,102,241,1); }
        """)
        self.expand_btn.clicked.connect(self._on_expand)
        exp_row.addWidget(self.close_btn)
        exp_row.addStretch()
        exp_row.addWidget(self.expand_btn)
        card_layout.addLayout(exp_row)

    def _reposition_input(self):
        self.input_bar.setGeometry(INPUT_X, BTN_Y, INPUT_W, self._input_h)

    def _on_input_changed(self):
        doc_h = int(self.input_bar.document().size().height()) + 10
        new_h = max(INPUT_MIN_H, min(doc_h, INPUT_MAX_H))
        if new_h != self._input_h:
            self._input_h = new_h
            self._reposition_input()
            self._resize()

    def _resize(self):
        cap_h = self._cap_h()
        if self._body_h > 0:
            self.card.setGeometry(15, cap_h, BODY_W, self._body_h)
            self.card.show()
        else:
            self.card.hide()
        self.setFixedSize(W, cap_h + self._body_h)
        self.update()

    def _update_body_height(self):
        content_h = self.chat_widget.sizeHint().height() + EXPAND_BTN + 24
        self._body_h = min(content_h, MAX_BODY_H) if self._has_messages() else 0
        self._resize()

    def _has_messages(self):
        return self.chat_layout.count() > 1

    # ── conversation ──────────────────────────────────────────────────────────
    def _load_active_conversation(self):
        conv = db.get_active_conversation()
        self.conv_id = conv[0]
        self._clear_chat()
        for role, content in db.get_messages(self.conv_id):
            self._add_bubble(content, role == "user")
        self._update_body_height()

    def _clear_chat(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_bubble(self, text, is_user):
        bubble = MessageBubble(text, is_user, self._theme)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        QTimer.singleShot(50, self._update_body_height)
        QTimer.singleShot(80, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

    def _send(self):
        text = self.input_bar.toPlainText().strip()
        if not text:
            return
        self.input_bar.clear()
        self._input_h = INPUT_MIN_H
        self._reposition_input()
        self._add_bubble(text, True)
        db.add_message(self.conv_id, "user", text)
        history = [{"role": r, "content": c} for r, c in db.get_messages(self.conv_id)]
        self.send_btn.setEnabled(False)
        self.plus_btn.setEnabled(False)
        self.worker = GroqWorker(history)
        self.worker.response_ready.connect(self._on_response)
        self.worker.start()
        # keep input focused so user can type next message
        self.input_bar.setFocus()

    def _on_response(self, reply):
        db.add_message(self.conv_id, "assistant", reply)
        self._add_bubble(reply, False)
        self.send_btn.setEnabled(True)
        self.plus_btn.setEnabled(True)
        self.input_bar.setFocus()

    def _new_conversation(self):
        self.conv_id = db.create_conversation()
        self._clear_chat()
        self._body_h = 0
        self._input_h = INPUT_MIN_H
        self._reposition_input()
        self._resize()

    def _on_expand(self):
        self.hide()
        self.open_main.emit()

    def eventFilter(self, obj, event):
        # close on outside click if input empty and no chat
        if event.type() == QEvent.MouseButtonPress and self.isVisible():
            if not self.geometry().contains(event.globalPos()):
                if not self.input_bar.toPlainText().strip() and not self._has_messages():
                    self.hide()
                    return False
        if obj == self.input_bar and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                if self.send_btn.isEnabled():
                    self._send()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(e.globalPos() - self.drag_pos)

    def _btn_css(self, accent):
        bg  = "rgba(99,102,241,0.35)" if accent else "rgba(30,30,50,0.9)"
        bgh = "rgba(99,102,241,0.65)" if accent else "rgba(99,102,241,0.45)"
        r   = BTN_D // 2
        return f"""
            QPushButton {{
                background:{bg}; border:1px solid rgba(255,255,255,0.13);
                border-radius:{r}px; color:rgba(255,255,255,0.85);
                font-size:18px; font-weight:bold;
            }}
            QPushButton:hover {{ background:{bgh}; color:white; }}
            QPushButton:disabled {{ color:rgba(255,255,255,0.3); }}
        """

    def show_near_cursor(self, prefill=""):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - W) // 2
        y = 20
        self.move(x, y)
        self._load_active_conversation()
        if prefill:
            self.input_bar.setPlainText(prefill)
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_bar.setFocus()

    def toggle(self):
        """Toggle popup — close if open, open if closed."""
        if self.isVisible():
            self.hide()
        else:
            self.show_near_cursor()
