# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
import html as html_mod
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer
import threading

from backend import copr, dnf_manager, system
from backend.validation import sanitize_full_name
from ui.terminal_dialog import TerminalOutputDialog
from ui.repo_details import RepoDetailsWindow
from ui.packages_window import PackagesWindow
from ui.styles import STYLESHEET


class SearchWorker(QThread):
    finished = pyqtSignal(list)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        results = copr.search_copr(self.query)
        self.finished.emit(results)


class InstalledWorker(QThread):
    finished = pyqtSignal(list)

    def run(self):
        mgr = dnf_manager.DNFManager()
        repos = mgr.list_configured_coprs()
        self.finished.emit(repos)


class MainWindow(QMainWindow):
    # Signal used to trigger load_installed_repos safely from a background thread.
    _request_refresh_installed = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CoprManagerQT")
        self.resize(900, 600)
        self.setStyleSheet(STYLESHEET)

        self.enabled_repos_set = set()

        self.check_system()
        self.setup_ui()
        self.load_installed_repos()

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(500)
        self.search_timer.timeout.connect(self.perform_search)
        self.current_search_text = ""

        # Connect refresh signal → load_installed_repos (always on main thread)
        self._request_refresh_installed.connect(self.load_installed_repos)

    # ------------------------------------------------------------------
    # System checks
    # ------------------------------------------------------------------

    def check_system(self):
        if not system.is_fedora():
            QMessageBox.warning(
                self, "System Warning",
                "This application is designed for Fedora Linux."
            )
        elif system.get_fedora_version() != 43:
            QMessageBox.warning(
                self, "Compatibility Warning",
                f"You are running Fedora {system.get_fedora_version()}.\n"
                "This tool is optimized for Fedora 43."
            )

        if not system.has_copr_cli():
            QMessageBox.critical(
                self, "Dependency Missing",
                "copr-cli is not installed.\n"
                "Please install it via: sudo dnf install copr-cli"
            )

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # --- Search Tab ---
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search COPR repositories...")
        self.search_entry.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_entry)

        self.search_status = QLabel(
            "Welcome to COPR Manager\n"
            "Search and enable community repositories for Fedora."
        )
        self.search_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.search_status.setProperty("class", "title-3")
        search_layout.addWidget(self.search_status)

        self.search_listbox = QListWidget()
        self.search_listbox.itemClicked.connect(self.on_search_item_clicked)
        self.search_listbox.hide()
        search_layout.addWidget(self.search_listbox)

        self.tabs.addTab(search_tab, "Search")

        # --- Installed Tab ---
        installed_tab = QWidget()
        installed_layout = QVBoxLayout(installed_tab)

        self.installed_listbox = QListWidget()
        installed_layout.addWidget(self.installed_listbox)

        self.tabs.addTab(installed_tab, "Installed")

    # ------------------------------------------------------------------
    # Search logic
    # ------------------------------------------------------------------

    def on_search_changed(self, text):
        if len(text) == 0:
            self.search_listbox.hide()
            self.search_status.setText(
                "Welcome to COPR Manager\n"
                "Search and enable community repositories for Fedora."
            )
            self.search_status.show()
            self.search_timer.stop()
            return

        if len(text) < 3:
            self.search_timer.stop()
            return

        self.search_status.setText("Searching...")
        self.search_status.show()
        self.search_listbox.hide()

        self.current_search_text = text
        self.search_timer.start()

    def perform_search(self):
        self.search_worker = SearchWorker(self.current_search_text)
        self.search_worker.finished.connect(self.update_search_results)
        self.search_worker.start()

    @pyqtSlot(list)
    def update_search_results(self, results):
        self.search_listbox.clear()

        if not results:
            self.search_status.setText("No Results Found")
            self.search_status.show()
            self.search_listbox.hide()
            return

        self.search_status.hide()
        self.search_listbox.show()

        for repo in results:
            item = QListWidgetItem(self.search_listbox)
            item.setData(Qt.ItemDataRole.UserRole, repo)

            widget = QWidget()
            layout = QHBoxLayout(widget)

            info_layout = QVBoxLayout()
            lbl_title = QLabel(html_mod.escape(repo.get("full_name", "Unknown")))
            lbl_title.setStyleSheet("font-weight: bold; font-size: 12pt;")
            info_layout.addWidget(lbl_title)

            # Escape description before displaying (COPR API data, untrusted)
            raw_desc = repo.get("description", "")[:100].replace("\n", " ")
            lbl_desc = QLabel(html_mod.escape(raw_desc))
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet("color: #666;")
            info_layout.addWidget(lbl_desc)

            layout.addLayout(info_layout)
            layout.addStretch()

            # Badges (built from known-safe badge text, not raw API data)
            badges = self.get_badges(repo)
            for text, style in badges:
                lbl_badge = QLabel(html_mod.escape(text))
                lbl_badge.setProperty("class", f"badge badge-{style}")
                layout.addWidget(lbl_badge)

            from PyQt6.QtCore import QSize
            hint = widget.sizeHint()
            item.setSizeHint(QSize(hint.width(), 80))
            self.search_listbox.setItemWidget(item, widget)

    def get_badges(self, repo):
        badges = []
        full_name = repo.get("full_name", "").lower()
        desc = repo.get("description", "").lower()
        owner = repo.get("owner", "").lower()

        if owner in ("fedora", "copr", "@copr", "@fedora"):
            badges.append(("Official", "accent"))
        elif owner.startswith("@"):
            badges.append(("Group", "neutral"))

        keywords = {
            "python": "Python", "rust": "Rust", "golang": "Go", "go ": "Go",
            "c++": "C++", "ruby": "Ruby", "java": "Java", "nodejs": "Node",
            "flask": "Python", "django": "Python", "gtk": "GTK", "qt": "Qt",
        }
        found_tech = set()
        for k, v in keywords.items():
            if k in desc or k in full_name:
                found_tech.add(v)
        for tech in list(found_tech)[:2]:
            badges.append((tech, "success"))

        desktops = {
            "gnome": "GNOME", "kde": "KDE", "cosmic": "Cosmic",
            "hyprland": "Hyprland", "sway": "Sway", "xfce": "XFCE",
        }
        for k, v in desktops.items():
            if k in desc or k in full_name:
                badges.append((v, "warning"))

        return badges

    def on_search_item_clicked(self, item):
        repo = item.data(Qt.ItemDataRole.UserRole)
        details = RepoDetailsWindow(repo, self)
        details.exec()

    # ------------------------------------------------------------------
    # Installed repos
    # ------------------------------------------------------------------

    def load_installed_repos(self):
        self.installed_worker = InstalledWorker()
        self.installed_worker.finished.connect(self.update_installed_list)
        self.installed_worker.start()

    @pyqtSlot(list)
    def update_installed_list(self, repos):
        self.installed_listbox.clear()
        self.enabled_repos_set.clear()

        if not repos:
            self.installed_listbox.addItem("No repositories configured.")
            return

        for repo in repos:
            is_enabled = repo.get("enabled", False)
            if is_enabled:
                self.enabled_repos_set.add(repo.get("full_name"))

            item = QListWidgetItem(self.installed_listbox)
            item.setData(Qt.ItemDataRole.UserRole, repo)

            widget = QWidget()
            layout = QHBoxLayout(widget)

            info_layout = QVBoxLayout()
            lbl_title = QLabel(html_mod.escape(repo.get("full_name", "Unknown")))
            lbl_title.setStyleSheet("font-weight: bold; font-size: 12pt;")
            info_layout.addWidget(lbl_title)

            status_text = "Enabled" if is_enabled else "Disabled"
            status_color = "green" if is_enabled else "gray"
            # status_text is safe (our own string); description is API data → escape it.
            escaped_desc = html_mod.escape(repo.get("description", ""))
            lbl_desc = QLabel(
                f'<span style="color:{status_color}">[{status_text}]</span> {escaped_desc}'
            )
            lbl_desc.setWordWrap(True)
            info_layout.addWidget(lbl_desc)

            layout.addLayout(info_layout)
            layout.addStretch()

            if is_enabled:
                btn_disable = QPushButton("Disable")
                btn_disable.clicked.connect(
                    lambda checked, r=repo: self._generic_repo_action(r, "disable")
                )
                layout.addWidget(btn_disable)

                btn_pkgs = QPushButton("Packages")
                btn_pkgs.clicked.connect(
                    lambda checked, r=repo: self.on_packages_clicked(r)
                )
                layout.addWidget(btn_pkgs)
            else:
                btn_enable = QPushButton("Enable")
                btn_enable.setProperty("class", "suggested-action")
                btn_enable.clicked.connect(
                    lambda checked, r=repo: self._generic_repo_action(r, "enable")
                )
                layout.addWidget(btn_enable)

            btn_remove = QPushButton("Remove")
            btn_remove.setProperty("class", "destructive-action")
            btn_remove.clicked.connect(
                lambda checked, r=repo: self.on_remove_repo_clicked(r)
            )
            layout.addWidget(btn_remove)

            from PyQt6.QtCore import QSize
            hint = widget.sizeHint()
            item.setSizeHint(QSize(hint.width(), 80))
            self.installed_listbox.setItemWidget(item, widget)

    def is_repo_enabled(self, full_name):
        return full_name in self.enabled_repos_set

    # ------------------------------------------------------------------
    # Common repo actions
    # ------------------------------------------------------------------

    def on_packages_clicked(self, repo):
        win = PackagesWindow(repo, self)
        win.exec()

    def on_remove_repo_clicked(self, repo):
        full_name = html_mod.escape(repo.get("full_name", ""))
        reply = QMessageBox.question(
            self, "Remove Repository?",
            f"Are you sure you want to remove the configuration for {full_name}?\n"
            "This will delete the .repo file.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._generic_repo_action(repo, "remove")

    def _generic_repo_action(self, repo, action):
        full_name = repo.get("full_name")
        if not full_name:
            return

        # Validate owner/project before handing to DNFManager.
        try:
            owner, project = sanitize_full_name(full_name)
        except ValueError as e:
            QMessageBox.critical(
                self, "Invalid Repository",
                f"Cannot perform action: {e}"
            )
            return

        title_map = {
            "enable":  f"Enabling {full_name}",
            "disable": f"Disabling {full_name}",
            "remove":  f"Removing {full_name}",
        }

        dlg = TerminalOutputDialog(
            title=title_map.get(action, "Processing"), parent=self
        )
        dlg.open()   # async-modal: blocks interaction with parent but doesn't block the thread

        def run_action():
            mgr = dnf_manager.DNFManager()

            def output_cb(line):
                dlg.append_line(line)

            success = False
            if action == "enable":
                success = mgr.enable_repo(owner, project, output_cb=output_cb)
            elif action == "disable":
                success = mgr.disable_repo(owner, project, output_cb=output_cb)
            elif action == "remove":
                success = mgr.remove_repo(owner, project, output_cb=output_cb)

            # set_finished emits a pyqtSignal internally — safe to call from any thread.
            dlg.set_finished(success)
            # Trigger installed-repos refresh on the main thread via a signal.
            # Do NOT use QTimer.singleShot from a background thread.
            self._request_refresh_installed.emit()

        thread = threading.Thread(target=run_action)
        thread.daemon = True
        thread.start()
