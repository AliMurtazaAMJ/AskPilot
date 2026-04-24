from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QSizePolicy,
    QApplication, QLineEdit, QFrame, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QEvent, QTimer
from PyQt5.QtGui import QPainter, QColor
import ctypes
import database as db
import groq_client
from styles import get_stylesheet

def _apply_stealth(hwnd):
    affinity = 0x11 if db.get_stealth() else 0x0
    ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity)

SIDEBAR_W = 220


class GroqWorker(QThread):
    response_ready = pyqtSignal(str)
    def __init__(self, messages):
        super().__init__()
        self.messages = messages
    def run(self):
        self.response_ready.emit(groq_client.get_response(self.messages))


class TestWorker(QThread):
    result = pyqtSignal(str, bool)  # (message, success)
    def __init__(self, key, model):
        super().__init__()
        self.key = key
        self.model = model
    def run(self):
        try:
            from groq import Groq
            resp = Groq(api_key=self.key).chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content":
                    "Reply with only the answer, nothing else. What is 47 + 36?"}],
                max_tokens=20,
            )
            answer = resp.choices[0].message.content
            if not answer or not answer.strip():
                self.result.emit(f"⚠ {self.model} — no response (model may be restricted)", False)
            else:
                self.result.emit(f"✓ {self.model} → {answer.strip()}", True)
        except Exception as e:
            err = str(e)
            if "model" in err.lower() or "not found" in err.lower() or "decommissioned" in err.lower():
                self.result.emit(f"⚠ Model not accessible: {err[:60]}", False)
            else:
                self.result.emit(f"✗ {err[:80]}", False)


class MessageBubble(QWidget):
    _MAX_W = 520

    def __init__(self, text, is_user, theme="dark", toast_fn=None):
        super().__init__()
        self._text = text
        self._is_user = is_user
        self.setStyleSheet("background: transparent;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        if theme == "light":
            css = ("QLabel{background:rgba(210,212,255,0.9);border:1px solid rgba(0,0,0,0.15);"
                   "border-radius:12px;padding:10px 14px;color:#000000;}") if is_user else \
                  ("QLabel{background:rgba(255,255,255,0.95);border:1px solid rgba(0,0,0,0.15);"
                   "border-radius:12px;padding:10px 14px;color:#000000;}")
            copy_color, copy_hover = "rgba(0,0,0,0.35)", "rgba(0,0,0,0.75)"
        else:
            css = ("QLabel{background:rgba(99,102,241,0.2);border:1px solid rgba(99,102,241,0.3);"
                   "border-radius:12px;padding:10px 14px;color:#e0e0ff;}") if is_user else \
                  ("QLabel{background:rgba(40,40,60,0.7);border:1px solid rgba(255,255,255,0.08);"
                   "border-radius:12px;padding:10px 14px;color:#d0d0d0;}")
            copy_color, copy_hover = "rgba(128,128,128,0.6)", "rgba(99,102,241,1)"

        self._label = QLabel(self._break_text(text))
        self._label.setWordWrap(True)
        self._label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self._label.setFixedWidth(self._MAX_W)
        self._label.setStyleSheet(css)

        copy_btn = QPushButton("⧉")
        copy_btn.setFixedSize(20, 20)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setToolTip("Copy")
        copy_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                          color:{copy_color}; font-size:12px; }}
            QPushButton:hover {{ color:{copy_hover}; }}
        """)
        def _copy():
            QApplication.clipboard().setText(self._text)
            if toast_fn:
                toast_fn()
        copy_btn.clicked.connect(_copy)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        if is_user:
            row.addStretch()
            row.addWidget(self._label)
            row.addWidget(copy_btn)
        else:
            row.addWidget(copy_btn)
            row.addWidget(self._label)
            row.addStretch()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w = min(self.width() - 30, self._MAX_W)
        if w > 0:
            self._label.setFixedWidth(w)

    @staticmethod
    def _break_text(text):
        """Insert zero-width spaces after every 40 chars in unspaced runs."""
        result = []
        run = 0
        for ch in text:
            result.append(ch)
            run = 0 if ch == ' ' else run + 1
            if run == 40:
                result.append('\u200b')  # zero-width space
                run = 0
        return ''.join(result)


class ConvItem(QWidget):
    clicked = pyqtSignal(int)
    renamed = pyqtSignal(int, str)
    deleted = pyqtSignal(int)

    def __init__(self, conv_id, title, is_active, icon_fg="rgba(255,255,255,0.25)"):
        super().__init__()
        self.conv_id = conv_id
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(6, 2, 4, 2)
        row.setSpacing(2)

        self.label = QPushButton(title)
        self.label.setObjectName("ConvItemActive" if is_active else "ConvItem")
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.label.setFixedHeight(30)
        self.label.clicked.connect(lambda: self.clicked.emit(self.conv_id))

        self.edit = QLineEdit(title)
        self.edit.setFixedHeight(26)
        self.edit.setStyleSheet("""
            QLineEdit { background:rgba(128,128,128,0.15);
                        border:1px solid rgba(99,102,241,0.5);
                        border-radius:6px; color:inherit;
                        padding:2px 6px; font-size:12px; }
        """)
        self.edit.hide()
        self.edit.returnPressed.connect(self._finish_edit)
        self.edit.editingFinished.connect(self._finish_edit)

        rename_b = QPushButton("✎")
        rename_b.setFixedSize(20, 20)
        rename_b.setCursor(Qt.PointingHandCursor)
        rename_b.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                          color:{icon_fg}; font-size:11px; }}
            QPushButton:hover {{ color:rgba(99,102,241,1); }}
        """)
        rename_b.clicked.connect(self._start_edit)

        del_b = QPushButton("🗑")
        del_b.setFixedSize(20, 20)
        del_b.setCursor(Qt.PointingHandCursor)
        del_b.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                          color:{icon_fg}; font-size:11px; }}
            QPushButton:hover {{ color:rgba(255,80,80,0.9); }}
        """)
        del_b.clicked.connect(lambda: self.deleted.emit(self.conv_id))

        row.addWidget(self.label, 1)
        row.addWidget(self.edit, 1)
        row.addWidget(rename_b)
        row.addWidget(del_b)

    def _start_edit(self):
        self.edit.setText(self.label.text())
        self.label.hide()
        self.edit.show()
        self.edit.setFocus()
        self.edit.selectAll()

    def _finish_edit(self):
        new_title = self.edit.text().strip() or self.label.text()
        self.label.setText(new_title)
        self.edit.hide()
        self.label.show()
        self.renamed.emit(self.conv_id, new_title)


class SettingsOverlay(QWidget):
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        self.card = QWidget(self)
        self.card.setFixedSize(420, 600)
        self.card.setStyleSheet("""
            QWidget {
                background: rgba(14,14,26,252);
                border-radius: 18px;
                border: 1px solid rgba(255,255,255,0.10);
            }
        """)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet("color:white;font-size:16px;font-weight:600;"
                            "background:transparent;border:none;")
        close = QPushButton("✕")
        close.setFixedSize(28, 28)
        close.setCursor(Qt.PointingHandCursor)
        close.setStyleSheet("""
            QPushButton{background:transparent;border:none;
                        color:rgba(255,255,255,0.4);font-size:15px;}
            QPushButton:hover{color:white;}
        """)
        close.clicked.connect(self.hide)
        hdr.addWidget(title); hdr.addStretch(); hdr.addWidget(close)
        layout.addLayout(hdr)
        layout.addWidget(self._sep())

        # ── Theme ──
        layout.addWidget(self._lbl("THEME"))
        theme_row = QHBoxLayout()
        theme_row.setSpacing(10)
        current = db.get_theme()
        self.dark_btn  = QPushButton("🌙  Dark")
        self.light_btn = QPushButton("☀️  Light")
        for btn in (self.dark_btn, self.light_btn):
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
        self._style_toggle(self.dark_btn,  current == "dark")
        self._style_toggle(self.light_btn, current == "light")
        self.dark_btn.clicked.connect(lambda: self._set_theme("dark"))
        self.light_btn.clicked.connect(lambda: self._set_theme("light"))
        theme_row.addWidget(self.dark_btn)
        theme_row.addWidget(self.light_btn)
        layout.addLayout(theme_row)
        layout.addWidget(self._sep())

        # ── Stealth ──
        layout.addWidget(self._lbl("STEALTH MODE"))
        stealth_row = QHBoxLayout()
        stealth_row.setSpacing(10)
        stealth_on = db.get_stealth()
        self.stealth_on_btn  = QPushButton("🔒  Hidden")
        self.stealth_off_btn = QPushButton("👁  Visible")
        for btn in (self.stealth_on_btn, self.stealth_off_btn):
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
        self._style_toggle(self.stealth_on_btn,  stealth_on)
        self._style_toggle(self.stealth_off_btn, not stealth_on)
        self.stealth_on_btn.clicked.connect(lambda: self._set_stealth(True))
        self.stealth_off_btn.clicked.connect(lambda: self._set_stealth(False))
        stealth_row.addWidget(self.stealth_on_btn)
        stealth_row.addWidget(self.stealth_off_btn)
        layout.addLayout(stealth_row)
        layout.addWidget(self._sep())

        # ── Model selector ──
        layout.addWidget(self._lbl("MODEL"))
        self.model_combo = QComboBox()
        self.model_combo.setFixedHeight(36)
        self.model_combo.setStyleSheet("""
            QComboBox{background:rgba(255,255,255,0.06);
                      border:1px solid rgba(255,255,255,0.12);
                      border-radius:10px;color:white;
                      padding:4px 12px;font-size:13px;}
            QComboBox:focus{border:1px solid rgba(99,102,241,0.6);}
            QComboBox QAbstractItemView{background:rgba(20,20,36,255);color:white;
                                        selection-background-color:rgba(99,102,241,0.5);}
        """)
        for m in groq_client.AVAILABLE_MODELS:
            self.model_combo.addItem(m)
        saved_model = db.get_selected_model() or groq_client.AVAILABLE_MODELS[0]
        idx = self.model_combo.findText(saved_model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.model_combo.currentTextChanged.connect(db.set_selected_model)
        layout.addWidget(self.model_combo)
        layout.addWidget(self._sep())

        # ── API Keys ──
        layout.addWidget(self._lbl("GROQ API KEYS  (tried in order, fallback if all fail)"))
        keys_scroll = QScrollArea()
        keys_scroll.setWidgetResizable(True)
        keys_scroll.setFixedHeight(100)
        keys_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        keys_scroll.setStyleSheet("""
            QScrollArea{background:transparent;border:none;}
            QScrollBar:vertical{background:transparent;width:4px;}
            QScrollBar::handle:vertical{background:rgba(255,255,255,0.15);border-radius:2px;}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
        """)
        keys_container = QWidget()
        keys_container.setStyleSheet("background:transparent;")
        self.keys_layout = QVBoxLayout(keys_container)
        self.keys_layout.setSpacing(4)
        self.keys_layout.setContentsMargins(0, 0, 4, 0)
        self.keys_layout.addStretch()
        keys_scroll.setWidget(keys_container)
        layout.addWidget(keys_scroll)
        self._refresh_keys()

        add_row = QHBoxLayout()
        add_row.setSpacing(6)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Add a Groq API key...")
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setFixedHeight(36)
        self.key_input.setStyleSheet("""
            QLineEdit{background:rgba(255,255,255,0.06);
                      border:1px solid rgba(255,255,255,0.12);
                      border-radius:10px;color:white;
                      padding:6px 12px;font-size:13px;}
            QLineEdit:focus{border:1px solid rgba(99,102,241,0.6);}
        """)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(36, 36)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton{background:rgba(99,102,241,0.4);
                        border:1px solid rgba(99,102,241,0.5);
                        border-radius:10px;color:white;font-size:18px;font-weight:bold;}
            QPushButton:hover{background:rgba(99,102,241,0.65);}
        """)
        add_btn.clicked.connect(self._add_key)
        add_row.addWidget(self.key_input, 1)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        self.status = QLabel("")
        self.status.setStyleSheet("color:rgba(99,241,150,0.85);font-size:12px;"
                                  "background:transparent;border:none;")
        layout.addWidget(self.status)
        layout.addStretch()

    def _refresh_keys(self):
        while self.keys_layout.count() > 1:
            item = self.keys_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for key in db.get_api_keys():
            row = QHBoxLayout()
            lbl = QLabel(key[:8] + "..." + key[-4:])
            lbl.setStyleSheet("color:rgba(255,255,255,0.6);font-size:12px;"
                              "background:transparent;border:none;")
            test_btn = QPushButton("Test")
            test_btn.setFixedHeight(22)
            test_btn.setCursor(Qt.PointingHandCursor)
            test_btn.setStyleSheet("""
                QPushButton{background:rgba(99,102,241,0.3);
                            border:1px solid rgba(99,102,241,0.5);
                            border-radius:6px;color:#a5b4fc;font-size:11px;padding:0 6px;}
                QPushButton:hover{background:rgba(99,102,241,0.55);color:white;}
                QPushButton:disabled{color:rgba(128,128,128,0.4);}
            """)
            test_btn.clicked.connect(lambda _, k=key, b=test_btn: self._test_key(k, b))
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(22, 22)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton{background:transparent;border:none;
                            color:rgba(255,80,80,0.6);font-size:11px;}
                QPushButton:hover{color:rgba(255,80,80,1);}
            """)
            del_btn.clicked.connect(lambda _, k=key: self._remove_key(k))
            row.addWidget(lbl, 1)
            row.addWidget(test_btn)
            row.addWidget(del_btn)
            w = QWidget()
            w.setStyleSheet("background:transparent;border:none;")
            w.setLayout(row)
            self.keys_layout.insertWidget(self.keys_layout.count() - 1, w)

    def _test_key(self, key, btn):
        model = self.model_combo.currentText()
        btn.setEnabled(False)
        btn.setText("...")
        self.status.setStyleSheet("color:rgba(255,255,255,0.5);font-size:12px;"
                                  "background:transparent;border:none;")
        self.status.setText(f"Testing {key[:8]}... with {model}")
        self._test_worker = TestWorker(key, model)
        self._test_worker.result.connect(lambda msg, ok, b=btn: self._on_test_result(msg, ok, b))
        self._test_worker.start()

    def _on_test_result(self, msg, ok, btn):
        btn.setEnabled(True)
        btn.setText("Test")
        color = "rgba(99,241,150,0.85)" if ok else "rgba(255,100,100,0.9)"
        self.status.setStyleSheet(f"color:{color};font-size:12px;"
                                   "background:transparent;border:none;")
        self.status.setText(msg)

    def _add_key(self):
        key = self.key_input.text().strip()
        if not key:
            return
        db.add_api_key(key)
        self.key_input.clear()
        self._refresh_keys()
        self.status.setText("✓ Key added")

    def _remove_key(self, key):
        db.remove_api_key(key)
        self._refresh_keys()
        self.status.setText("Key removed")

    def _sep(self):
        f = QFrame(); f.setFrameShape(QFrame.HLine)
        f.setStyleSheet("background:rgba(255,255,255,0.08);border:none;max-height:1px;")
        return f

    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet("color:rgba(255,255,255,0.45);font-size:10px;font-weight:700;"
                        "letter-spacing:1.2px;background:transparent;border:none;")
        return l

    def _style_toggle(self, btn, active):
        if active:
            btn.setStyleSheet("""
                QPushButton{background:rgba(99,102,241,0.5);
                            border:1px solid rgba(99,102,241,0.7);
                            border-radius:10px;color:white;font-weight:600;}
            """)
        else:
            btn.setStyleSheet("""
                QPushButton{background:rgba(255,255,255,0.07);
                            border:1px solid rgba(255,255,255,0.12);
                            border-radius:10px;color:rgba(255,255,255,0.55);}
                QPushButton:hover{background:rgba(255,255,255,0.13);color:white;}
            """)

    def _set_theme(self, theme):
        db.set_theme(theme)
        self._style_toggle(self.dark_btn,  theme == "dark")
        self._style_toggle(self.light_btn, theme == "light")
        self.theme_changed.emit(theme)

    def _set_stealth(self, enabled):
        db.set_stealth(enabled)
        self._style_toggle(self.stealth_on_btn,  enabled)
        self._style_toggle(self.stealth_off_btn, not enabled)
        for w in QApplication.topLevelWidgets():
            if w.isVisible() and w.winId():
                ctypes.windll.user32.SetWindowDisplayAffinity(
                    int(w.winId()), 0x11 if enabled else 0x0)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))
        p.end()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.card.move(
            (self.width()  - self.card.width())  // 2,
            (self.height() - self.card.height()) // 2,
        )

    def mousePressEvent(self, e):
        if not self.card.geometry().contains(e.pos()):
            self.hide()


class MainWindow(QWidget):
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.conv_id  = None
        self.drag_pos = None
        self._theme   = db.get_theme()
        self._conv_icon_fg = "rgba(0,0,0,0.4)" if self._theme == "light" else "rgba(255,255,255,0.25)"
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(900, 620)
        self._build_ui()
        self.apply_theme(self._theme)
        self._load_sidebar()
        self._open_conversation(db.get_active_conversation()[0])

    def apply_theme(self, theme):
        self._theme = theme
        self.setStyleSheet(get_stylesheet(theme))
        is_light = theme == "light"
        self._conv_icon_fg = "rgba(0,0,0,0.4)" if is_light else "rgba(255,255,255,0.25)"
        input_fg = "#000000" if is_light else "white"
        gear_fg  = "rgba(0,0,0,0.45)" if is_light else "rgba(255,255,255,0.3)"

        self.input_bar.setStyleSheet(f"""
            QTextEdit {{ background:transparent; border:none;
                        color:{input_fg}; font-size:13px; font-family:'Segoe UI'; }}
        """)
        self.gear_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                          color:{gear_fg}; font-size:18px;
                          text-align:left; padding-left:14px; }}
            QPushButton:hover {{ color:rgba(99,102,241,1); }}
        """)
        self._load_sidebar()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget(objectName="MainContainer")
        ml = QVBoxLayout(self.container)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        tb_w = QWidget(objectName="TitleBar")
        tb_w.setFixedHeight(38)
        tb = QHBoxLayout(tb_w)
        tb.setContentsMargins(16, 0, 8, 0)
        tb.addWidget(QLabel("AskPilot", objectName="TitleLabel"))
        tb.addStretch()
        for txt, slot in [("—", self.showMinimized), ("✕", self.hide)]:
            b = QPushButton(txt, objectName="MinBtn" if txt == "—" else "CloseBtn")
            b.setFixedSize(28, 24)
            b.clicked.connect(slot)
            tb.addWidget(b)
        ml.addWidget(tb_w)

        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)

        sidebar = QWidget(objectName="Sidebar")
        sidebar.setFixedWidth(SIDEBAR_W)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 8, 0, 0)
        sl.setSpacing(0)

        new_btn = QPushButton("+ New Chat", objectName="NewChatBtn")
        new_btn.clicked.connect(self._new_conversation)
        sl.addWidget(new_btn)

        self.conv_scroll = QScrollArea()
        self.conv_scroll.setWidgetResizable(True)
        self.conv_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.conv_scroll.setObjectName("ChatArea")
        self.conv_list_widget = QWidget()
        self.conv_list_layout = QVBoxLayout(self.conv_list_widget)
        self.conv_list_layout.setSpacing(0)
        self.conv_list_layout.setContentsMargins(0, 0, 0, 0)
        self.conv_list_layout.addStretch()
        self.conv_scroll.setWidget(self.conv_list_widget)
        sl.addWidget(self.conv_scroll, 1)

        self.gear_btn = QPushButton("⚙")
        self.gear_btn.setFixedHeight(38)
        self.gear_btn.setCursor(Qt.PointingHandCursor)
        self.gear_btn.clicked.connect(self._toggle_settings)
        sl.addWidget(self.gear_btn)

        body.addWidget(sidebar)

        chat_panel = QWidget()
        cpl = QVBoxLayout(chat_panel)
        cpl.setContentsMargins(12, 12, 12, 12)
        cpl.setSpacing(8)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setObjectName("ChatArea")
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setSpacing(8)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_widget)
        cpl.addWidget(self.chat_scroll, 1)

        capsule = QWidget()
        capsule.setStyleSheet("""
            QWidget { background:rgba(128,128,128,0.08);
                      border:1px solid rgba(128,128,128,0.2);
                      border-radius:22px; }
        """)
        cap_row = QHBoxLayout(capsule)
        cap_row.setContentsMargins(14, 6, 6, 6)
        cap_row.setSpacing(6)

        self.input_bar = QTextEdit()
        self.input_bar.setFixedHeight(56)
        self.input_bar.setPlaceholderText("Ask anything...  (Enter to send, Shift+Enter for newline)")
        self.input_bar.setLineWrapMode(QTextEdit.WidgetWidth)
        self.input_bar.installEventFilter(self)

        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton { background:rgba(99,102,241,0.4);
                          border:1px solid rgba(99,102,241,0.5);
                          border-radius:20px; color:#a5b4fc; font-size:16px; }
            QPushButton:hover { background:rgba(99,102,241,0.65); color:white; }
            QPushButton:disabled { color:rgba(128,128,128,0.4);
                                   background:rgba(99,102,241,0.15); }
        """)
        self.send_btn.clicked.connect(self._send)
        cap_row.addWidget(self.input_bar, 1)
        cap_row.addWidget(self.send_btn)
        cpl.addWidget(capsule)

        body.addWidget(chat_panel, 1)
        ml.addLayout(body, 1)
        root.addWidget(self.container)

        self.settings_overlay = SettingsOverlay(self.container)
        self.settings_overlay.theme_changed.connect(self._on_theme_changed)
        self.settings_overlay.hide()

        # toast label — sits at bottom-center of container
        self._toast = QLabel("Message copied", self.container)
        self._toast.setAttribute(Qt.WA_StyledBackground, True)
        self._toast.setAlignment(Qt.AlignCenter)
        self._toast.setStyleSheet("""
            QLabel { background:rgba(99,102,241,0.92); color:#ffffff;
                     border:none; border-radius:20px;
                     padding:8px 22px; font-size:12px;
                     font-family:'Segoe UI'; font-weight:600; }
        """)
        self._toast.adjustSize()
        self._toast.hide()
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._toast.hide)

    def _on_theme_changed(self, theme):
        self.apply_theme(theme)
        self.theme_changed.emit(theme)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.settings_overlay.setGeometry(
            0, 0, self.container.width(), self.container.height())
        self._toast.adjustSize()
        self._toast.move(
            (self.container.width() - self._toast.width()) // 2,
            self.container.height() - self._toast.height() - 20)

    def show_toast(self):
        self._toast_timer.stop()
        self._toast.adjustSize()
        self._toast.move(
            (self.container.width() - self._toast.width()) // 2,
            self.container.height() - self._toast.height() - 20)
        self._toast.show()
        self._toast.raise_()
        self._toast_timer.start(1800)

    def _toggle_settings(self):
        if self.settings_overlay.isVisible():
            self.settings_overlay.hide()
        else:
            self.settings_overlay.setGeometry(
                0, 0, self.container.width(), self.container.height())
            self.settings_overlay.show()
            self.settings_overlay.raise_()

    def _load_sidebar(self):
        while self.conv_list_layout.count() > 1:
            item = self.conv_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        active = db.get_active_conversation()
        for conv in db.get_all_conversations():
            item = ConvItem(conv[0], conv[1], conv[0] == active[0],
                            self._conv_icon_fg)
            item.clicked.connect(self._open_conversation)
            item.renamed.connect(self._rename_conversation)
            item.deleted.connect(self._delete_conversation)
            self.conv_list_layout.insertWidget(
                self.conv_list_layout.count() - 1, item)

    def _rename_conversation(self, conv_id, title):
        with db.get_conn() as conn:
            conn.execute("UPDATE conversations SET title=? WHERE id=?", (title, conv_id))

    def _delete_conversation(self, conv_id):
        db.delete_conversation(conv_id)
        remaining = db.get_all_conversations()
        self._open_conversation(remaining[0][0] if remaining else db.create_conversation())

    def _open_conversation(self, conv_id):
        db.set_active_conversation(conv_id)
        self.conv_id = conv_id
        self._clear_chat()
        for role, content in db.get_messages(conv_id):
            self._add_bubble(content, role == "user")
        self._load_sidebar()

    def _clear_chat(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _add_bubble(self, text, is_user):
        bubble = MessageBubble(text, is_user, self._theme, toast_fn=self.show_toast)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum())

    def _send(self):
        text = self.input_bar.toPlainText().strip()
        if not text:
            return
        self.input_bar.clear()
        self._add_bubble(text, True)
        db.add_message(self.conv_id, "user", text)
        history = [{"role": r, "content": c} for r, c in db.get_messages(self.conv_id)]
        self.send_btn.setEnabled(False)
        self.worker = GroqWorker(history)
        self.worker.response_ready.connect(self._on_response)
        self.worker.start()
        self.input_bar.setFocus()

    def _on_response(self, reply):
        db.add_message(self.conv_id, "assistant", reply)
        self._add_bubble(reply, False)
        self.send_btn.setEnabled(True)
        self.input_bar.setFocus()
        self._load_sidebar()

    def _new_conversation(self):
        self._open_conversation(db.create_conversation())

    def eventFilter(self, obj, event):
        if obj == self.input_bar and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                if self.send_btn.isEnabled():
                    self._send()
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, e):
        super().showEvent(e)
        _apply_stealth(int(self.winId()))
