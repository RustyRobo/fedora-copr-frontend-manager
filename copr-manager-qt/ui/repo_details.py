# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
import html as html_mod
import webbrowser

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QGroupBox
)
from PyQt6.QtCore import Qt


def _e(value) -> str:
    """Return HTML-escaped string for safe insertion into Qt rich text."""
    if value is None:
        return ""
    return html_mod.escape(str(value))


class RepoDetailsWindow(QDialog):
    def __init__(self, repo, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.parent_window = parent
        self.setWindowTitle("Repository Details")
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # Scroll area for details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # --- Title ---
        lbl_title = QLabel(_e(repo.get("full_name", "Unknown")))
        lbl_title.setProperty("class", "title-1")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(lbl_title)

        # --- Description ---
        grp_desc = QGroupBox("Description")
        l_desc = QVBoxLayout(grp_desc)
        lbl_desc = QLabel(_e(repo.get("description", "No description available.")))
        lbl_desc.setWordWrap(True)
        lbl_desc.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # Plain text only — disable rich-text rendering to prevent HTML injection.
        lbl_desc.setTextFormat(Qt.TextFormat.PlainText)
        l_desc.addWidget(lbl_desc)
        content_layout.addWidget(grp_desc)

        # --- Instructions ---
        grp_instr = QGroupBox("Instructions")
        l_instr = QVBoxLayout(grp_instr)
        lbl_instr = QLabel(
            _e(repo.get("instructions", "No specific instructions provided."))
        )
        lbl_instr.setWordWrap(True)
        lbl_instr.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl_instr.setTextFormat(Qt.TextFormat.PlainText)
        l_instr.addWidget(lbl_instr)
        content_layout.addWidget(grp_instr)

        # --- Metadata ---
        grp_meta = QGroupBox("Metadata")
        l_meta = QVBoxLayout(grp_meta)

        # Supported Versions (from chroot names — safe, we control parsing)
        chroots = repo.get("chroots")
        if chroots:
            versions = set()
            iterable = chroots.keys() if isinstance(chroots, dict) else chroots
            for chroot in iterable:
                parts = chroot.split("-")
                if "fedora" in parts:
                    try:
                        idx = parts.index("fedora")
                        ver = parts[idx + 1]
                        if ver.isdigit() or ver == "rawhide":
                            versions.add(f"Fedora {ver}")
                    except (IndexError, ValueError):
                        pass
                elif "epel" in parts:
                    try:
                        idx = parts.index("epel")
                        ver = parts[idx + 1]
                        if ver.isdigit():
                            versions.add(f"EPEL {ver}")
                    except (IndexError, ValueError):
                        pass

            if versions:
                sorted_vers = sorted(
                    list(versions),
                    key=lambda x: x.split()[-1],
                    reverse=True,
                )
                # Version strings are built by us from chroot names — safe to bold.
                ver_text = ", ".join(sorted_vers)
                lbl_ver = QLabel(f"<b>Supported Versions:</b> {_e(ver_text)}")
                l_meta.addWidget(lbl_ver)

        size_bytes = repo.get("storage_usage")
        if size_bytes:
            try:
                size_mb = int(size_bytes) / 1024 / 1024
                lbl_size = QLabel(f"<b>Storage Usage:</b> {size_mb:.1f}\u202fMB")
                l_meta.addWidget(lbl_size)
            except (ValueError, TypeError):
                pass

        homepage = repo.get("homepage")
        if homepage:
            # Escape the URL so it can't break the href attribute or inject tags.
            safe_url = _e(homepage)
            lbl_home = QLabel(f"<b>Homepage:</b> <a href='{safe_url}'>{safe_url}</a>")
            lbl_home.setOpenExternalLinks(True)
            l_meta.addWidget(lbl_home)

        contact = repo.get("contact")
        if contact:
            lbl_contact = QLabel(f"<b>Contact:</b> {_e(contact)}")
            lbl_contact.setTextFormat(Qt.TextFormat.RichText)
            lbl_contact.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            l_meta.addWidget(lbl_contact)

        content_layout.addWidget(grp_meta)

        # --- Bottom action bar ---
        bottom_bar = QHBoxLayout()
        bottom_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_bar.setSpacing(10)
        content_layout.addLayout(bottom_bar)

        full_name = repo.get("full_name")

        is_enabled = False
        if hasattr(self.parent_window, "is_repo_enabled"):
            is_enabled = self.parent_window.is_repo_enabled(full_name)

        if is_enabled:
            btn_pkgs = QPushButton("Open Packages")
            btn_pkgs.clicked.connect(self.on_open_packages)
            bottom_bar.addWidget(btn_pkgs)

            btn_disable = QPushButton("Disable Repository")
            btn_disable.setProperty("class", "destructive-action")
            btn_disable.clicked.connect(self.on_disable_clicked)
            bottom_bar.addWidget(btn_disable)
        else:
            btn_enable = QPushButton("Enable Repository")
            btn_enable.setProperty("class", "suggested-action")
            btn_enable.clicked.connect(self.on_enable_clicked)
            bottom_bar.addWidget(btn_enable)

        if homepage and "github.com" in homepage:
            btn_source = QPushButton("Source Code")
            btn_source.clicked.connect(lambda: webbrowser.open(homepage))
            bottom_bar.addWidget(btn_source)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def on_open_packages(self):
        if hasattr(self.parent_window, "on_packages_clicked"):
            self.parent_window.on_packages_clicked(self.repo)
        self.accept()

    def on_disable_clicked(self):
        if hasattr(self.parent_window, "_generic_repo_action"):
            self.parent_window._generic_repo_action(self.repo, "disable")
        self.accept()

    def on_enable_clicked(self):
        if hasattr(self.parent_window, "_generic_repo_action"):
            self.parent_window._generic_repo_action(self.repo, "enable")
        self.accept()
