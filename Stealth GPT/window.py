import webview
import ctypes
import win32gui
import os
from config import APP_NAME, DATA_DIR


_window = None
_visible = True


def _hide_from_taskbar():
    hwnd = win32gui.FindWindow(None, APP_NAME)
    if not hwnd:
        return
    GWL_EXSTYLE = -20
    GWL_STYLE = -16
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000
    WS_SYSMENU = 0x00080000
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000

    ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex = (ex | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)

    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
    style = style | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_THICKFRAME
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

    ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
        0x0020 | 0x0002 | 0x0001 | 0x0004)

    win32gui.SetWindowText(hwnd, " ")


def _apply_stealth():
    hwnd = win32gui.FindWindow(None, APP_NAME)
    if hwnd:
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)


def _hook_close():
    import time
    time.sleep(1.5)
    try:
        import clr
        from System.ComponentModel import CancelEventArgs
        wpf = _window.native
        if wpf:
            def on_closing(sender, args):
                args.Cancel = True
                toggle()
            wpf.Closing += on_closing
    except Exception:
        pass


def create():
    global _window
    _window = webview.create_window(
        APP_NAME,
        "https://chatgpt.com",
        width=1000,
        height=700,
        resizable=True,
        on_top=True,
    )


def start():
    os.makedirs(DATA_DIR, exist_ok=True)
    webview.start(private_mode=False, storage_path=DATA_DIR)


def toggle():
    global _window, _visible
    if _window:
        if _visible:
            _window.hide()
            _visible = False
        else:
            _window.show()
            _visible = True
            _apply_stealth()
            _hide_from_taskbar()


def hide_on_startup():
    import time
    time.sleep(1.0)
    global _window, _visible
    if _window and _visible:
        _window.hide()
        _visible = False
        _apply_stealth()
        _hide_from_taskbar()


def destroy():
    if _window:
        _window.destroy()
