# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # We can set a style or let Qt use system default.
    # We will use some basic custom QSS for a modern look.
    app.setStyle("Fusion") 
    
    window = MainWindow()
    window.show()
    
    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
