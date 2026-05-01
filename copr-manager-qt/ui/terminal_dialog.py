# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal, pyqtSlot

class TerminalOutputDialog(QDialog):
    append_text_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, title="Terminal Output", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(700, 500)
        
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel(title + " (Running...)")
        self.title_label.setProperty("class", "title-3")
        layout.addWidget(self.title_label)
        
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        # basic terminal look
        self.text_edit.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: monospace;")
        layout.addWidget(self.text_edit)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False)
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close)
        
        # Connect signals to slots so threads can safely update UI
        self.append_text_signal.connect(self.on_append_line)
        self.finished_signal.connect(self.on_finished)

    @pyqtSlot(str)
    def on_append_line(self, text):
        self.text_edit.appendPlainText(text)
        # Scroll to bottom is handled automatically by QPlainTextEdit.appendPlainText
        
    @pyqtSlot(bool)
    def on_finished(self, success):
        self.btn_close.setEnabled(True)
        self.btn_close.setFocus()          # grab focus so it's immediately usable

        if success:
            self.title_label.setText(self.windowTitle() + " — Completed Successfully")
            self.text_edit.appendPlainText("\n--- Operation Completed Successfully ---")
            self.btn_close.setProperty("class", "suggested-action")
        else:
            self.title_label.setText(self.windowTitle() + " — Failed")
            self.text_edit.appendPlainText("\n--- Operation Failed ---")

        # Force Qt to re-evaluate the stylesheet for the button's new enabled/class state
        # and trigger a synchronous repaint so the button visually becomes clickable.
        self.btn_close.style().unpolish(self.btn_close)
        self.btn_close.style().polish(self.btn_close)
        self.btn_close.update()            # schedule repaint
        self.btn_close.repaint()           # force immediate repaint

    def append_line(self, text):
        # This can be called safely from any thread if we use signals, 
        # but to be sure, we emit the signal.
        self.append_text_signal.emit(text)

    def set_finished(self, success):
        self.finished_signal.emit(success)
