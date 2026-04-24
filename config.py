DB_PATH         = "chatbot.db"
APP_NAME        = "AskPilot"
HOTKEY          = "ctrl+shift+z"
_FALLBACK_KEY   = "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"
_FALLBACK_MODEL = "llama-3.1-8b-instant"

import os, sys

_STARTUP_DIR = os.path.join(
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
)
_STARTUP_VBS = os.path.join(_STARTUP_DIR, f"{APP_NAME}.vbs")

def enable_startup():
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    vbs = f'CreateObject("WScript.Shell").Run """ & Chr(34) & "{pythonw}" & Chr(34) & " " & Chr(34) & "{script}" & Chr(34) & """, 0, False'
    with open(_STARTUP_VBS, "w") as f:
        f.write(vbs)

def disable_startup():
    if os.path.exists(_STARTUP_VBS):
        os.remove(_STARTUP_VBS)

def is_startup_enabled():
    return os.path.exists(_STARTUP_VBS)
