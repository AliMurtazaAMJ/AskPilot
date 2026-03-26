DARK_GLASS = """
    QWidget {
        background: transparent;
        color: #e0e0e0;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }
    #MainContainer {
        background: rgba(15, 15, 25, 215);
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.08);
    }
    #TitleBar {
        background: rgba(255,255,255,0.04);
        border-top-left-radius: 16px;
        border-top-right-radius: 16px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    #TitleLabel { color: rgba(255,255,255,0.7); font-size:13px; font-weight:600; }
    #CloseBtn, #MinBtn {
        background: transparent; border: none;
        color: rgba(255,255,255,0.4); font-size:16px;
        padding: 2px 8px; border-radius: 6px;
    }
    #CloseBtn:hover { background: rgba(255,80,80,0.3); color: white; }
    #MinBtn:hover   { background: rgba(255,255,255,0.1); color: white; }
    #Sidebar {
        background: rgba(255,255,255,0.03);
        border-right: 1px solid rgba(255,255,255,0.06);
        border-bottom-left-radius: 16px;
    }
    #NewChatBtn {
        background: rgba(99,102,241,0.25);
        border: 1px solid rgba(99,102,241,0.4);
        border-radius: 10px; color: #a5b4fc;
        font-weight: 600; padding: 8px; margin: 8px;
    }
    #NewChatBtn:hover { background: rgba(99,102,241,0.4); }
    #ConvItem {
        background: transparent; border: none;
        border-radius: 8px; color: rgba(255,255,255,0.6);
        text-align: left; padding: 6px 10px;
    }
    #ConvItem:hover { background: rgba(255,255,255,0.07); color: white; }
    #ConvItemActive {
        background: rgba(99,102,241,0.2);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 8px; color: #a5b4fc;
        text-align: left; padding: 6px 10px;
    }
    #ChatArea { background: transparent; border: none; }
    #UserBubble {
        background: rgba(99,102,241,0.2);
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 12px; padding: 10px 14px; color: #e0e0ff;
    }
    #BotBubble {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px; padding: 10px 14px; color: #d0d0d0;
    }
    QScrollBar:vertical { background: transparent; width: 4px; }
    QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius: 2px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

LIGHT_GLASS = """
    QWidget {
        background: transparent;
        color: #0a0a0a;
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }
    #MainContainer {
        background: rgba(240, 242, 248, 245);
        border-radius: 16px;
        border: 1px solid rgba(0,0,0,0.18);
    }
    #TitleBar {
        background: rgba(255,255,255,0.85);
        border-top-left-radius: 16px;
        border-top-right-radius: 16px;
        border-bottom: 1px solid rgba(0,0,0,0.12);
    }
    #TitleLabel { color: #0a0a0a; font-size:13px; font-weight:600; }
    #CloseBtn, #MinBtn {
        background: transparent; border: none;
        color: rgba(0,0,0,0.45); font-size:16px;
        padding: 2px 8px; border-radius: 6px;
    }
    #CloseBtn:hover { background: rgba(255,60,60,0.15); color: #c00; }
    #MinBtn:hover   { background: rgba(0,0,0,0.07); color: #000; }
    #Sidebar {
        background: rgba(255,255,255,0.7);
        border-right: 1px solid rgba(0,0,0,0.12);
        border-bottom-left-radius: 16px;
    }
    #NewChatBtn {
        background: rgba(99,102,241,0.12);
        border: 1px solid rgba(0,0,0,0.15);
        border-radius: 10px; color: #1a1aaa;
        font-weight: 600; padding: 8px; margin: 8px;
    }
    #NewChatBtn:hover { background: rgba(99,102,241,0.22); }
    #ConvItem {
        background: transparent; border: none;
        border-radius: 8px; color: #111111;
        text-align: left; padding: 6px 10px;
    }
    #ConvItem:hover { background: rgba(0,0,0,0.06); color: #000; }
    #ConvItemActive {
        background: rgba(99,102,241,0.14);
        border: 1px solid rgba(0,0,0,0.15);
        border-radius: 8px; color: #1a1aaa;
        text-align: left; padding: 6px 10px;
    }
    #ChatArea { background: transparent; border: none; }
    #UserBubble {
        background: rgba(210,212,255,0.85);
        border: 1px solid rgba(0,0,0,0.15);
        border-radius: 12px; padding: 10px 14px;
        color: #000000;
    }
    #BotBubble {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(0,0,0,0.15);
        border-radius: 12px; padding: 10px 14px;
        color: #000000;
    }
    QScrollBar:vertical { background: transparent; width: 4px; }
    QScrollBar::handle:vertical { background: rgba(0,0,0,0.18); border-radius: 2px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def get_stylesheet(theme: str) -> str:
    return LIGHT_GLASS if theme == "light" else DARK_GLASS
