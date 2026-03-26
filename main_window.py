from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QSizePolicy,
    QApplication, QLineEdit, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QEvent
from PyQt5.QtGui import QPainter, QColor
import database as db
import groq_client
from styles import get_stylesheet

SIDEBAR_W = 220


class GroqWorker(QThread):
    response_ready = pyqtSignal(str)
    def __init__(self, messages):
        super().__init__()
        self.messages = messages
    def run(self):
        self.response_ready.emit(groq_client.get_response(self.messages))


class MessageBubble(QWidget):
    def __init__(self, text, is_user, theme="dark"):
        super().__init__()
        self._text = text
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        label = QLabel(text)
        label.setObjectName("UserBubble" if is_user else "BotBubble")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        label.setMaximumWidth(520)

        # override bubble colors for light mode since QSS #objectName
        # may not propagate through transparent parents reliably
        if theme == "light":
            if is_user:
                label.setStyleSheet(
                    "background:rgba(210,212,255,0.9);border:1px solid rgba(0,0,0,0.15);"
                    "border-radius:12px;padding:10px 14px;color:#000000;")
            else:
                label.setStyleSheet(
                    "background:rgba(255,255,255,0.95);border:1px solid rgba(0,0,0,0.15);"
                    "border-radius:12px;padding:10px 14px;color:#000000;")
            copy_color = "rgba(0,0,0,0.35)"
            copy_hover = "rgba(0,0,0,0.75)"
        else:
            if is_user:
                label.setStyleSheet(
                    "background:rgba(99,102,241,0.2);border:1px solid rgba(99,102,241,0.3);"
                    "border-radius:12px;padding:10px 14px;color:#e0e0ff;")
            else:
                label.setStyleSheet(
                    "background:rgba(40,40,60,0.7);border:1px solid rgba(255,255,255,0.08);"
                    "border-radius:12px;padding:10px 14px;color:#d0d0d0;")
            copy_color = "rgba(128,128,128,0.6)"
            copy_hover = "rgba(99,102,241,1)"

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

        if is_user:
            row.addStretch()
            row.addWidget(label)
            row.addWidget(copy_btn)
        else:
            row.addWidget(copy_btn)
            row.addWidget(label)
            row.addStretch()


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
        self.card.setFixedSize(400, 480)
        self.card.setStyleSheet("""
            QWidget {
                background: rgba(14,14,26,252);
                border-radius: 18px;
                border: 1px solid rgba(255,255,255,0.10);
            }
        """)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)

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

        layout.addWidget(self._lbl("THEME"))
        theme_row = QHBoxLayout()
        theme_row.setSpacing(10)
        current = db.get_theme()
        self.dark_btn  = QPushButton("🌙  Dark")
        self.light_btn = QPushButton("☀️  Light")
        for btn in (self.dark_btn, self.light_btn):
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
        self._style_theme_btn(self.dark_btn,  current == "dark")
        self._style_theme_btn(self.light_btn, current == "light")
        self.dark_btn.clicked.connect(lambda: self._set_theme("dark"))
        self.light_btn.clicked.connect(lambda: self._set_theme("light"))
        theme_row.addWidget(self.dark_btn)
        theme_row.addWidget(self.light_btn)
        layout.addLayout(theme_row)
        layout.addWidget(self._sep())

        layout.addWidget(self._lbl("GROQ API KEY"))
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Enter your Groq API key...")
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setFixedHeight(40)
        self.api_input.setStyleSheet("""
            QLineEdit{background:rgba(255,255,255,0.06);
                      border:1px solid rgba(255,255,255,0.12);
                      border-radius:10px;color:white;
                      padding:8px 12px;font-size:13px;}
            QLineEdit:focus{border:1px solid rgba(99,102,241,0.6);}
        """)
        saved = db.get_api_key()
        if saved:
            self.api_input.setText(saved)
        layout.addWidget(self.api_input)

        save_btn = QPushButton("Save API Key")
        save_btn.setFixedHeight(38)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton{background:rgba(99,102,241,0.35);
                        border:1px solid rgba(99,102,241,0.5);
                        border-radius:10px;color:#a5b4fc;
                        font-size:13px;font-weight:600;}
            QPushButton:hover{background:rgba(99,102,241,0.55);color:white;}
        """)
        save_btn.clicked.connect(self._save_api)
        layout.addWidget(save_btn)

        self.status = QLabel("")
        self.status.setStyleSheet("color:rgba(99,241,150,0.85);font-size:12px;"
                                  "background:transparent;border:none;")
        layout.addWidget(self.status)
        layout.addWidget(self._sep())

        layout.addWidget(self._lbl("ABOUT"))
        about = QLabel("AskPilot — Your AI, one shortcut away.\n"
                       "Press Ctrl+Shift+W anywhere to ask instantly.")
        about.setWordWrap(True)
        about.setStyleSheet("color:rgba(255,255,255,0.4);font-size:12px;"
                            "background:transparent;border:none;")
        layout.addWidget(about)
        layout.addStretch()

    def _sep(self):
        f = QFrame(); f.setFrameShape(QFrame.HLine)
        f.setStyleSheet("background:rgba(255,255,255,0.08);border:none;max-height:1px;")
        return f

    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet("color:rgba(255,255,255,0.45);font-size:10px;font-weight:700;"
                        "letter-spacing:1.2px;background:transparent;border:none;")
        return l

    def _style_theme_btn(self, btn, active):
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
        self._style_theme_btn(self.dark_btn,  theme == "dark")
        self._style_theme_btn(self.light_btn, theme == "light")
        self.theme_changed.emit(theme)

    def _save_api(self):
        key = self.api_input.text().strip()
        db.set_api_key(key)
        self.status.setText("✓ Saved" if key else "Cleared")

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
        self.setWindowFlags(Qt.FramelessWindowHint)
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

    def _on_theme_changed(self, theme):
        self.apply_theme(theme)
        self.theme_changed.emit(theme)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.settings_overlay.setGeometry(
            0, 0, self.container.width(), self.container.height())

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
        bubble = MessageBubble(text, is_user, self._theme)
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

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self.drag_pos:
            self.move(e.globalPos() - self.drag_pos)
