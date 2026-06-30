import os, sys

APP_NAME        = "Stealth GPT"
HOTKEY          = "ctrl+shift+g"

DATA_DIR        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stealth_gpt_data")

_APPDATA      = os.environ.get("APPDATA", "")
_SCRIPT       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
_PYTHONW      = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
_STARTUP_DIR  = os.path.join(_APPDATA, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
_STARTUP_VBS  = os.path.join(_STARTUP_DIR, f"{APP_NAME}.vbs")

def _write_vbs(path):
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
