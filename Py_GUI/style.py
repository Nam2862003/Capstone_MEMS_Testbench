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
    padding: 5px;
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
    padding: 5px;
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
}

QComboBox QAbstractItemView::item:disabled {
    color: #777777;
    background-color: #1a1a1a;
}

QComboBox QAbstractItemView::item:disabled:selected {
    background: #1a1a1a;
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

/* =========================
   TITLE LABEL
========================= */

QLabel#Title {
    font-size: 28px;
    font-weight: bold;
    color: #ffffff;
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

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    top: -3px;
    padding: 0 6px;
    background-color: #121212;
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
"""