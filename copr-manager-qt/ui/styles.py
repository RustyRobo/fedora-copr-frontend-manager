# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
STYLESHEET = """
QWidget {
    font-size: 11pt;
}

QListWidget {
    border: none;
    background-color: transparent;
}

QListWidget::item {
    border-bottom: 1px solid #ddd;
    padding: 10px;
}

QListWidget::item:selected {
    background-color: #0078D7;
    color: white;
}

QPushButton {
    padding: 6px 12px;
    border: 1px solid #777;
    border-radius: 4px;
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.1);
}

QPushButton.suggested-action {
    background-color: #0078D7;
    color: white;
    border: none;
}

QPushButton.suggested-action:hover {
    background-color: #005A9E;
}

QPushButton.destructive-action {
    background-color: #D13438;
    color: white;
    border: none;
}

QPushButton.destructive-action:hover {
    background-color: #A4262C;
}

QLabel.title-1 {
    font-size: 18pt;
    font-weight: bold;
}

QLabel.title-3 {
    font-size: 14pt;
    font-weight: bold;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #ccc;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 5px;
}

QLabel.badge {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 9pt;
    font-weight: bold;
}

QLabel.badge-accent {
    background-color: #E1DFDD;
    color: #323130;
}

QLabel.badge-success {
    background-color: #DFF6DD;
    color: #107C10;
}

QLabel.badge-warning {
    background-color: #FFF4CE;
    color: #797775;
}

QLabel.badge-neutral {
    background-color: #F3F2F1;
    color: #605E5C;
}
"""
