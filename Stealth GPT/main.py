import sys
import threading
import os
import ctypes
import ctypes.wintypes
import win32event
import win32api
import winerror
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from config import APP_NAME, HOTKEY, enable_startup, is_startup_enabled
from window import create, start, toggle, hide_on_startup, destroy, _hook_close


MSG = ctypes.wintypes.MSG
user32 = ctypes.windll.user32


def _hotkey_thread():
    hwnd = user32.CreateWindowExW(
        0, "STATIC", None, 0,
        0, 0, 0, 0,
        ctypes.wintypes.HWND(-3),
        0, 0, None
    )

    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    VK_G = 0x47

    user32.RegisterHotKey(hwnd, 1, MOD_CONTROL | MOD_SHIFT, VK_G)

    msg = MSG()
    while True:
        ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if ret <= 0:
            break
        if msg.message == 0x0312:
            toggle()

    user32.UnregisterHotKey(hwnd, 1)
    user32.DestroyWindow(hwnd)


def make_tray_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=(99, 102, 241, 255))
    draw.text((16, 18), "SG", fill="white")
    return img


def run_tray():
    def on_toggle(_):
        toggle()

    def on_quit(_):
        icon.stop()
        destroy()
        os._exit(0)

    icon = Icon(
        APP_NAME,
        make_tray_icon(),
        menu=Menu(
            MenuItem("Open / Hide", on_toggle, default=True),
            MenuItem("Quit", on_quit),
        )
    )
    icon.run()


def main():
    mutex = win32event.CreateMutex(None, False, f"Global\\{APP_NAME}_mutex")
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        sys.exit(0)

    if not is_startup_enabled():
        enable_startup()

    create()

    threading.Thread(target=_hotkey_thread, daemon=True).start()
    threading.Thread(target=hide_on_startup, daemon=True).start()
    threading.Thread(target=_hook_close, daemon=True).start()
    threading.Thread(target=run_tray, daemon=True).start()

    start()


if __name__ == "__main__":
    main()
