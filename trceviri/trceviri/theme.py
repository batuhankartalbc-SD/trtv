"""Koyu tema — tasarım görsellerindeki renkler (lacivert-siyah zemin, nane yeşili vurgu, mor tuşlar)."""

ACCENT = "#3EE6A0"
ACCENT_DARK = "#0F2A21"
BG = "#0A0E13"
SIDEBAR = "#0C1117"
CARD = "#10161D"
CARD2 = "#131A22"
BORDER = "#1E2731"
TEXT = "#E8EDF2"
MUTED = "#8C98A6"
PURPLE = "#B79CFF"
PURPLE_BG = "#211A38"
RED = "#F87171"

QSS = f"""
* {{ font-family: 'Segoe UI Variable Display', 'Segoe UI'; font-size: 14px; color: {TEXT}; }}
QMainWindow, QWidget#root, QStackedWidget, QStackedWidget > QWidget, QDialog {{ background: {BG}; }}
QWidget#sidebar {{ background: {SIDEBAR}; border-right: 1px solid {BORDER}; }}
QLabel#logo {{ font-size: 24px; font-weight: 700; }}
QPushButton#nav {{ text-align: left; padding: 12px 16px; border: none; border-radius: 10px;
    font-size: 16px; background: transparent; color: {TEXT}; border-left: 3px solid transparent; }}
QPushButton#nav:hover {{ background: #121A20; }}
QPushButton#nav:checked {{ background: {ACCENT_DARK}; border-left: 3px solid {ACCENT}; font-weight: 600; }}
QLabel#h1 {{ font-size: 34px; font-weight: 700; }}
QLabel#h2 {{ font-size: 26px; font-weight: 700; }}
QLabel#sub {{ color: {MUTED}; font-size: 14px; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#small {{ color: {MUTED}; font-size: 12px; }}
QLabel#cardtitle {{ font-size: 20px; font-weight: 700; }}
QLabel#field {{ font-size: 15px; font-weight: 600; }}
QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; }}
QFrame#card2 {{ background: {CARD2}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#sep {{ background: {BORDER}; max-height: 1px; min-height: 1px; border: none; }}
QFrame#vsep {{ background: {BORDER}; max-width: 1px; min-width: 1px; border: none; }}
QPushButton {{ background: {CARD2}; border: 1px solid #263240; border-radius: 10px; padding: 9px 16px; font-size: 14px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #5B6672; border-color: {BORDER}; }}
QPushButton#primary {{ background: {ACCENT}; color: #04140D; font-weight: 700; border: none; }}
QPushButton#primary:hover {{ background: #63F0B6; }}
QPushButton#primary:disabled {{ background: #1F4A3A; color: #7FA898; }}
QPushButton#outlineGreen {{ border: 1px solid {ACCENT}; color: {TEXT}; background: transparent; }}
QPushButton#danger {{ border: 1px solid {PURPLE}; color: {PURPLE}; background: transparent; }}
QPushButton#seg {{ border-radius: 0; padding: 8px 16px; background: {CARD2}; min-width: 118px; }}
QPushButton#seg:checked {{ background: {ACCENT}; color: #04140D; font-weight: 700; border-color: {ACCENT}; }}
QPushButton#iconbtn {{ background: transparent; border: none; padding: 4px; }}
QPushButton#iconbtn:hover {{ background: #1A232C; border-radius: 6px; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: #0D1319; border: 1px solid #263240;
    border-radius: 10px; padding: 8px 12px; selection-background-color: {ACCENT}; selection-color: #04140D; font-size: 14px; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{ background: {CARD}; border: 1px solid {BORDER}; selection-background-color: {ACCENT_DARK}; padding: 4px; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 18px; border: none; }}
QTableWidget {{ background: transparent; border: none; gridline-color: {BORDER}; font-size: 14px; }}
QTableWidget::item {{ padding: 6px 10px; border-bottom: 1px solid {BORDER}; }}
QTableWidget::item:selected {{ background: #142029; color: {TEXT}; }}
QHeaderView {{ background: {CARD}; border: none; }}
QTableCornerButton::section {{ background: {CARD}; border: none; }}
QHeaderView::section {{ background: {CARD}; color: #C5CED8; border: none; border-bottom: 1px solid {BORDER};
    padding: 10px; font-weight: 600; font-size: 14px; text-align: left; }}
QRadioButton {{ spacing: 10px; }}
QRadioButton::indicator {{ width: 18px; height: 18px; border-radius: 10px; border: 2px solid #4A5664; background: transparent; }}
QRadioButton::indicator:checked {{ border: 2px solid {ACCENT}; background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
    stop:0 {ACCENT}, stop:0.45 {ACCENT}, stop:0.5 transparent); }}
QCheckBox {{ spacing: 10px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid #4A5664; background: #0D1319; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}
QSlider::groove:horizontal {{ height: 6px; background: #2A3440; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }}
QPlainTextEdit {{ background: #0D1319; border: 1px solid {BORDER}; border-radius: 10px; font-family: Consolas; font-size: 12px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: #2A3533; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QLabel#key {{ background: {PURPLE_BG}; color: {PURPLE}; border: 1px solid #3B2F63; border-radius: 6px; padding: 4px 12px; font-weight: 700; }}
QLabel#pill_on {{ background: #123A2C; color: {ACCENT}; border-radius: 9px; padding: 3px 10px; font-weight: 600; }}
QLabel#pill_off {{ background: #1C232C; color: {MUTED}; border-radius: 9px; padding: 3px 10px; font-weight: 600; }}
QLabel#chip {{ background: #2A2250; color: #D9CCFF; border-radius: 6px; padding: 2px 8px; font-size: 12px; }}
QListWidget {{ background: transparent; border: none; }}
QToolTip {{ background: {CARD}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px; }}
"""
