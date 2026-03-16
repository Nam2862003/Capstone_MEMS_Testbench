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
    font-size: 15px;
    border-radius: 6px;
    padding: 8px 16px;
}

QPushButton:hover {
    background-color: #2893ff;
}

QPushButton:pressed {
    background-color: #005a9e;
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


/* =========================
   PR PAGE TAB COLOR
   (Piezoresistive)
========================= */

QTabWidget#PRTabs QTabBar::tab:selected {
    background: #2e8b57;
}


/* =========================
   PE PAGE TAB COLOR
   (Piezoelectric)
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
"""