# AskPilot

AskPilot is a lightweight Windows desktop AI assistant powered by Groq. It lives in your system tray and lets you ask questions instantly from anywhere using a global hotkey — no browser, no switching windows.

---

## Features

- **Global Hotkey** — Press `Ctrl+Shift+Z` anywhere to open the floating popup
- **Selected Text Prefill** — Select text before pressing the hotkey to auto-fill it as your question
- **Floating Popup** — Compact, always-on-top chat widget that stays out of your way
- **Full Chat Window** — Expand to a full-featured chat with conversation history sidebar
- **Multiple Conversations** — Create, rename, and delete chat sessions
- **Dark / Light Theme** — Switch themes from Settings; preference is saved
- **Custom Groq API Key** — Use your own key via Settings; falls back to a built-in key
- **System Tray** — Runs silently in the background; right-click tray icon to open or quit

---

## Requirements

- Windows 10/11
- Python 3.10+

---

## Installation

```bash
git clone https://github.com/AliMurtazaAMJ/AskPilot.git
cd AskPilot
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py
```

The app starts minimized to the system tray.

| Action | How |
|---|---|
| Open popup | `Ctrl+Shift+Z` |
| Ask with selected text | Select text → `Ctrl+Shift+Z` |
| Expand to full window | Click `↗` in popup, or tray → *Open AskPilot* |
| New conversation | Click `+` in popup or `+ New Chat` in sidebar |
| Settings (theme / API key) | Click `⚙` in the sidebar |
| Quit | Right-click tray icon → *Quit* |

---

## Configuration

| File | Purpose |
|---|---|
| `config.py` | Default hotkey, Groq model, DB path |
| `database.py` | SQLite storage for chats, settings, API key |
| `groq_client.py` | Groq API wrapper with user-key / fallback logic |

To change the hotkey, edit `HOTKEY` in `config.py`:

```python
HOTKEY = "ctrl+shift+z"
```

---

## Project Structure

```
AskPilot/
├── main.py          # Entry point, hotkey listener, tray icon
├── popup.py         # Floating mini-chat popup
├── main_window.py   # Full chat window with sidebar
├── groq_client.py   # Groq API calls
├── database.py      # SQLite helpers
├── styles.py        # Dark / light QSS stylesheets
├── config.py        # App-wide constants
└── requirements.txt
```

---

## Dependencies

```
PyQt5
groq
keyboard
pystray
Pillow
pywin32
```

---

## License

MIT
