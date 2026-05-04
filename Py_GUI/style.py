STYLE = """
/* =========================
   GLOBAL WINDOW
========================= */

QWidget {
    background-color: #121212;
    color: #e0e0e0;
}

/* =========================
   BUTTONS
========================= */

QPushButton {
    background-color: #0078d4;
    color: white;
    font-size: 13px;
    border-radius: 6px;
    padding: 4px 10px;
}

QPushButton:hover {
    background-color: #2893ff;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #777777;
    border: 1px solid #3a3a3a;
}

/* =========================
   LINE EDIT
========================= */

QLineEdit {
    background-color: #1f1f1f;
    color: #e0e0e0;
    border: 1px solid #444;
    padding: 5px 5px 5px 8px;
    border-radius: 4px;
}

QLineEdit:disabled {
    background-color: #1a1a1a;
    color: #777777;
    border: 1px solid #333;
}

/* =========================
   COMBO BOX
========================= */

QComboBox {
    background-color: #1f1f1f;
    border: 1px solid #444;
    padding: 5px 24px 5px 8px;
    border-radius: 4px;
}

QComboBox:hover {
    border: 1px solid #0078d4;
}

QComboBox:disabled {
    background-color: #1a1a1a;
    color: #777777;
    border: 1px solid #333;
}

QComboBox QAbstractItemView {
    background-color: #1f1f1f;
    color: #e0e0e0;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
    outline: 0;
}

QComboBox QAbstractItemView::item {
    padding: 6px 8px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #0078d4;
    color: #ffffff;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #0078d4;
    color: #ffffff;
}

QComboBox QAbstractItemView::item:disabled {
    color: #777777;
    background-color: #1a1a1a;
}

QComboBox QAbstractItemView::item:disabled:selected {
    background: #1a1a1a;
}

QMenu {
    background-color: #1f1f1f;
    color: #e0e0e0;
    border: 1px solid #d9d9d9;
}

QMenu::item {
    background-color: transparent;
    padding: 6px 28px 6px 12px;
}

QMenu::item:selected {
    background-color: #0078d4;
    color: #ffffff;
}

QWidget#ActuatorField {
    background-color: #1f1f1f;
    color: #e0e0e0;
    border: 1px solid #444;
    border-radius: 4px;
}

QWidget#ActuatorField:hover {
    border: 1px solid #0078d4;
}

QWidget#ActuatorField:disabled {
    background-color: #1a1a1a;
    color: #777777;
    border: 1px solid #333;
}

QLabel#ActuatorDisplay {
    background: transparent;
    border: none;
    padding: 5px 8px;
    font-size: 13px;
}

QLabel#ActuatorDisplay:disabled {
    color: #777777;
}

QToolButton#ActuatorArrow {
    background: transparent;
    color: #e0e0e0;
    border: none;
    padding: 0 8px 0 4px;
}

QToolButton#ActuatorArrow:disabled {
    color: #777777;
}

QToolButton#ActuatorArrow::menu-indicator {
    image: none;
    width: 0px;
}

/* =========================
   TABS (GENERAL)
========================= */

QTabWidget::pane {
    border: 1px solid #444;
    background: #181818;
}

QTabBar::tab {
    background: #2a2a2a;
    color: #cccccc;
    padding: 8px 18px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}

QTabBar::tab:selected {
    background: #0078d4;
    color: white;
}

QTabBar::tab:hover {
    background: #3a3a3a;
}

QTabBar::tab:disabled {
    color: #777777;
    background-color: #1a1a1a;
    border: 1px solid #333;
}

/* =========================
   PR PAGE TAB COLOR
========================= */

QTabWidget#PRTabs QTabBar::tab:selected {
    background: #2e8b57;
}

/* =========================
   PE PAGE TAB COLOR
========================= */

QTabWidget#PETabs QTabBar::tab:selected {
    background: #c05621;
}

/* =========================
   LABELS
========================= */

QLabel {
    font-size: 15px;
}

QLabel:disabled {
    color: #777777;
}

/* =========================
   TITLE LABEL
========================= */

QLabel#Title {
    font-size: 28px;
    font-weight: bold;
    color: #ffffff;
}

QLabel#MutedLabel {
    color: #b8b8b8;
    font-size: 13px;
}

/* =========================
   GROUP BOX (PANELS)
========================= */

QGroupBox {
    border: 1px solid #555;
    border-radius: 8px;
    margin-top: 15px;
    padding-top: 10px;
}

QGroupBox:disabled {
    color: #777777;
    border: 1px solid #333;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    top: -3px;
    padding: 0 6px;
    background-color: #121212;
}

QSlider#DiscreteSlider::groove:horizontal {
    border: 1px solid #444;
    height: 6px;
    background: #1f1f1f;
    border-radius: 3px;
}

QSlider#DiscreteSlider::sub-page:horizontal {
    background: #0078d4;
    border-radius: 3px;
}

QSlider#DiscreteSlider::add-page:horizontal {
    background: #2a2a2a;
    border-radius: 3px;
}

QSlider#DiscreteSlider::handle:horizontal {
    background: #e0e0e0;
    border: 1px solid #cfcfcf;
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
}

QSlider#DiscreteSlider::handle:horizontal:hover {
    background: #ffffff;
}

QSlider#DiscreteSlider::tick-mark:horizontal {
    background: #666666;
    width: 1px;
    height: 6px;
}

/* =========================
   GROUP CHECKBOXES
========================= */

QCheckBox {
    font-size: 14px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    background-color: #1f1f1f;
    border: 1px solid #444;
}

QCheckBox::indicator:checked {
    background-color: #0078d4;
    border: 1px solid #0078d4;
}

QCheckBox#CursorToggle::indicator {
    width: 18px;
    height: 18px;
    background-color: #121212;
    border: 2px solid #7a7a7a;
}

QCheckBox#CursorToggle::indicator:unchecked {
    image: none;
    background-color: #121212;
    border: 2px solid #7a7a7a;
}

QCheckBox#CursorToggle::indicator:checked {
    background-color: #121212;
    border: 2px solid #7a7a7a;
    image: url(assets/cursor-check.svg);
}
"""
