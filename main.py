import sys
import threading
import keyboard
import win32clipboard
import win32con
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import database as db
from popup import PopupWindow
from main_window import MainWindow
from config import HOTKEY, APP_NAME


class Bridge(QObject):
    show_popup = pyqtSignal(str)
    show_main = pyqtSignal()


def get_selected_text():
    """Grab currently selected text via clipboard trick."""
    try:
        old = ""
        try:
            win32clipboard.OpenClipboard()
            old = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
        except:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.CloseClipboard()

        keyboard.send("ctrl+c")
        time.sleep(0.15)

        selected = ""
        try:
            win32clipboard.OpenClipboard()
            selected = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
        except:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass

        # Restore old clipboard
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            if old:
                win32clipboard.SetClipboardText(old, win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
        except:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass

        return selected.strip() if selected != old else ""
    except Exception:
        return ""


def make_tray_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=(99, 102, 241, 255))
    draw.text((20, 18), "H", fill="white")
    return img


def run_tray(bridge):
    def on_open(_):
        bridge.show_main.emit()

    def on_quit(_):
        icon.stop()
        QApplication.quit()

    icon = Icon(
        APP_NAME,
        make_tray_icon(),
        menu=Menu(
            MenuItem("Open AskPilot", on_open, default=True),
            MenuItem("Quit", on_quit),
        )
    )
    icon.run()


def main():
    db.init_db()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    bridge = Bridge()
    popup = PopupWindow()
    main_win = MainWindow()

    def trigger_popup():
        selected = get_selected_text()
        bridge.show_popup.emit(selected)

    def on_hotkey():
        threading.Thread(target=trigger_popup, daemon=True).start()

    def _show_main():
        popup.hide()
        main_win.show()
        main_win.raise_()
        main_win.activateWindow()

    bridge.show_popup.connect(lambda text: popup.toggle() if not text and popup.isVisible() else popup.show_near_cursor(text))
    bridge.show_main.connect(_show_main)
    popup.open_main.connect(_show_main)
    main_win.theme_changed.connect(popup.apply_theme)

    keyboard.add_hotkey(HOTKEY, on_hotkey)

    tray_thread = threading.Thread(target=run_tray, args=(bridge,), daemon=True)
    tray_thread.start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
