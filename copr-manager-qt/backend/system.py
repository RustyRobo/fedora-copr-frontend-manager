# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
import shutil
import platform

def is_fedora() -> bool:
    try:
        with open("/etc/os-release") as f:
            content = f.read()
            return "ID=fedora" in content
    except FileNotFoundError:
        return False

def get_fedora_version() -> int:
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("VERSION_ID="):
                    return int(line.strip().split("=")[1])
    except (FileNotFoundError, ValueError, IndexError):
        return 0
    return 0

def has_copr_cli() -> bool:
    return shutil.which("copr-cli") is not None

def has_dnf() -> bool:
    return shutil.which("dnf") is not None
