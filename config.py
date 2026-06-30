import os, sys

APP_NAME        = "AskPilot"
HOTKEY          = "ctrl+shift+z"
_FALLBACK_KEY   = "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"
_FALLBACK_MODEL = "llama-3.1-8b-instant"

DB_PATH         = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot.db")

_APPDATA      = os.environ.get("APPDATA", "")
_SCRIPT       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
_PYTHONW      = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
_STARTUP_DIR  = os.path.join(_APPDATA, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
_STARTUP_VBS  = os.path.join(_STARTUP_DIR, f"{APP_NAME}.vbs")
_DESKTOP      = os.path.join(os.path.expanduser("~"), "Desktop")
_DESKTOP_LNK  = os.path.join(_DESKTOP, f"{APP_NAME}.lnk")

def _write_vbs(path):
    # Clean VBScript: one line, no string concatenation issues
    vbs = (
        'Set sh = CreateObject("WScript.Shell")\n'
        f'sh.Run Chr(34) & "{_PYTHONW}" & Chr(34) & " " & Chr(34) & "{_SCRIPT}" & Chr(34), 0, False\n'
    )
    with open(path, "w") as f:
        f.write(vbs)

def enable_startup():
    _write_vbs(_STARTUP_VBS)

def disable_startup():
    if os.path.exists(_STARTUP_VBS):
        os.remove(_STARTUP_VBS)

def is_startup_enabled():
    return os.path.exists(_STARTUP_VBS)

def create_shortcut():
    import win32com.client
    shell = win32com.client.Dispatch("WScript.Shell")
    lnk = shell.CreateShortcut(_DESKTOP_LNK)
    lnk.TargetPath      = _PYTHONW
    lnk.Arguments       = f'"{_SCRIPT}"'
    lnk.WorkingDirectory = os.path.dirname(_SCRIPT)
    lnk.Description     = APP_NAME
    lnk.save()

def remove_shortcut():
    if os.path.exists(_DESKTOP_LNK):
        os.remove(_DESKTOP_LNK)

def is_shortcut_exists():
    return os.path.exists(_DESKTOP_LNK)
