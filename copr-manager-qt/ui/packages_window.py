# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
import html as html_mod
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, QSize

from backend import dnf_manager
from ui.terminal_dialog import TerminalOutputDialog


class PackagesWorker(QThread):
    finished = pyqtSignal(list, dict, str)

    def __init__(self, repo_id):
        super().__init__()
        self.repo_id = repo_id

    def run(self):
        mgr = dnf_manager.DNFManager()
        pkgs = mgr.list_packages(self.repo_id)

        pkg_status = {}
        for p in pkgs:
            pkg_status[p] = mgr.is_package_installed(p)

        self.finished.emit(pkgs, pkg_status, self.repo_id)


class PackagesWindow(QDialog):
    # Signal used to trigger load_packages safely from a background thread.
    # pyqtSignal is always delivered on the receiver's (main) thread.
    _request_refresh = pyqtSignal()

    def __init__(self, repo, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.parent_window = parent
        self.setWindowTitle(f"Packages: {repo.get('full_name')}")
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        self.status = QLabel("Loading packages...")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setMargin(10)
        layout.addWidget(self.status)

        self.listbox = QListWidget()
        layout.addWidget(self.listbox)

        # Connect refresh signal → load_packages (always on main thread)
        self._request_refresh.connect(self.load_packages)

        self.load_packages()

    @pyqtSlot()
    def load_packages(self):
        full_name = self.repo.get("full_name", "")
        if "/" not in full_name:
            return
        owner, project = full_name.split("/", 1)
        repo_id = f"copr:copr.fedorainfracloud.org:{owner}:{project}"

        self.worker = PackagesWorker(repo_id)
        self.worker.finished.connect(self.update_list_with_status)
        self.worker.start()

    @pyqtSlot(list, dict, str)
    def update_list_with_status(self, pkgs, pkg_status, repo_id):
        self.listbox.clear()

        if not pkgs:
            self.status.setText(
                f"No packages found or repo not enabled/found ({repo_id})."
            )
            return

        self.status.setText(f"Found {len(pkgs)} packages.")

        for pkg in pkgs:
            item = QListWidgetItem(self.listbox)
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(5, 5, 5, 5)

            lbl_name = QLabel(html_mod.escape(pkg))
            row_layout.addWidget(lbl_name)
            row_layout.addStretch()

            is_installed = pkg_status.get(pkg, False)
            if is_installed:
                btn = QPushButton("Remove")
                btn.setProperty("class", "destructive-action")
                btn.clicked.connect(lambda checked, p=pkg: self.on_remove_clicked(p))
            else:
                btn = QPushButton("Install")
                btn.setProperty("class", "suggested-action")
                btn.clicked.connect(lambda checked, p=pkg: self.on_install_clicked(p))

            row_layout.addWidget(btn)

            hint = row_widget.sizeHint()
            item.setSizeHint(QSize(hint.width(), 60))
            self.listbox.setItemWidget(item, row_widget)

    def on_install_clicked(self, pkg):
        self._generic_package_action(pkg, "install")

    def on_remove_clicked(self, pkg):
        self._generic_package_action(pkg, "remove")

    def _generic_package_action(self, pkg_name, action):
        title_map = {
            "install": f"Installing {pkg_name}",
            "remove":  f"Removing {pkg_name}",
        }

        dlg = TerminalOutputDialog(
            title=title_map.get(action, "Processing"), parent=self
        )
        dlg.open()  # async-modal: blocks parent without blocking the thread

        def run_action():
            mgr = dnf_manager.DNFManager()

            def output_cb(line):
                # append_line emits a signal internally — thread-safe
                dlg.append_line(line)

            success = False
            if action == "install":
                success = mgr.install_package(pkg_name, output_cb=output_cb)
            elif action == "remove":
                success = mgr.remove_package(pkg_name, output_cb=output_cb)

            # set_finished emits a pyqtSignal (finished_signal) which PyQt6
            # automatically delivers on the main thread via a queued connection.
            # Calling it directly from a background thread is safe and correct.
            dlg.set_finished(success)

            # Trigger load_packages on the main thread via a dedicated signal.
            # Do NOT use QTimer.singleShot from a background thread — it posts
            # to the background thread's event loop (which doesn't exist).
            self._request_refresh.emit()

        import threading
        thread = threading.Thread(target=run_action, daemon=True)
        thread.start()
