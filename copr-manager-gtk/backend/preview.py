# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
import subprocess
import logging
from typing import Dict, List

from backend.validation import validate_package_name

logger = logging.getLogger(__name__)


class PreviewManager:
    """
    Handles 'dry-run' preview of DNF operations via --assumeno.
    """

    def get_install_preview(self, package_name: str) -> Dict[str, List[str]]:
        """
        Run `dnf install <pkg> --assumeno` to preview what would change.

        Returns a dict with keys: 'install', 'upgrade', 'remove', 'downgrade'.
        Returns an empty dict on error.
        """
        # Validate package name before it touches any subprocess call.
        try:
            package_name = validate_package_name(package_name)
        except ValueError as e:
            logger.error(f"get_install_preview validation error: {e}")
            return {}

        # "--" explicitly terminates option parsing so package_name can never
        # be interpreted as a dnf flag, even if it starts with "--".
        cmd = ["dnf", "install", "--assumeno", "--", package_name]

        try:
            # LC_ALL=C ensures English output for reliable parsing.
            # PATH is restricted to known safe locations.
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env={"LC_ALL": "C", "PATH": "/usr/bin:/usr/local/bin:/bin"},
            )
            return self._parse_dnf_transaction(result.stdout)
        except Exception as e:
            logger.error(f"Preview failed: {e}")
            return {}

    def _parse_dnf_transaction(self, output: str) -> Dict[str, List[str]]:
        """
        Parse the tabular output of DNF to categorize packages by action.

        Example section header patterns (DNF4 and DNF5):
            Installing:
            Installing dependencies:
            Upgrading:
            Removing:
            Downgrading:
        """
        changes: Dict[str, List[str]] = {
            "install": [],
            "upgrade": [],
            "remove": [],
            "downgrade": [],
        }

        current_section = None
        _SKIP_PREFIXES = ("=", "-", "Package", "Summary", "Total", "Transaction")

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            lower = line.lower()

            # Identify section headers
            if lower.startswith("installing"):
                current_section = "install"
                continue
            elif lower.startswith("upgrading"):
                current_section = "upgrade"
                continue
            elif lower.startswith("removing"):
                current_section = "remove"
                continue
            elif lower.startswith("downgrading"):
                current_section = "downgrade"
                continue

            # Skip separator / header lines
            if any(line.startswith(p) for p in _SKIP_PREFIXES):
                continue

            if current_section and " " in line:
                parts = line.split()
                if parts:
                    pkg = parts[0]
                    if pkg not in ("Name", "Package") and "Transaction" not in line:
                        changes[current_section].append(pkg)

        return changes
