# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
import subprocess
import logging
from typing import List, Dict, Optional

from backend.validation import (
    validate_owner,
    validate_project,
    validate_package_name,
    validate_host,
    validate_repo_id,
    sanitize_full_name,
)

logger = logging.getLogger(__name__)


class DNFManager:
    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def run_streaming_command(self, cmd: List[str], output_cb=None) -> bool:
        """
        Run a command and stream output line-by-line to output_cb.
        Blocks until the command finishes; output_cb is called in-thread.
        """
        logger.info(f"Running streaming command: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line-buffered
        )

        if output_cb:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    output_cb(line.strip())
        else:
            process.wait()

        return process.returncode == 0

    # ------------------------------------------------------------------
    # Repository management
    # ------------------------------------------------------------------

    def enable_repo(self, owner: str, project: str, output_cb=None) -> bool:
        """Enable a COPR repository using pkexec dnf copr enable."""
        try:
            owner = validate_owner(owner)
            project = validate_project(project)
        except ValueError as e:
            logger.error(f"enable_repo validation error: {e}")
            return False

        repo_slug = f"{owner}/{project}"
        cmd = ["pkexec", "dnf", "copr", "enable", "-y", repo_slug]

        if output_cb:
            return self.run_streaming_command(cmd, output_cb)

        logger.info(f"Enabling repo: {repo_slug}")
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to enable repo {repo_slug}: {e}")
            return False

    def disable_repo(self, owner: str, project: str, output_cb=None) -> bool:
        """Disable a COPR repository using pkexec dnf copr disable."""
        try:
            owner = validate_owner(owner)
            project = validate_project(project)
        except ValueError as e:
            logger.error(f"disable_repo validation error: {e}")
            return False

        repo_slug = f"{owner}/{project}"
        cmd = ["pkexec", "dnf", "copr", "disable", "-y", repo_slug]

        if output_cb:
            return self.run_streaming_command(cmd, output_cb)

        logger.info(f"Disabling repo: {repo_slug}")
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to disable repo {repo_slug}: {e}")
            return False

    def remove_repo(self, owner: str, project: str, output_cb=None) -> bool:
        """Remove a COPR repository configuration using pkexec dnf copr remove."""
        try:
            owner = validate_owner(owner)
            project = validate_project(project)
        except ValueError as e:
            logger.error(f"remove_repo validation error: {e}")
            return False

        repo_slug = f"{owner}/{project}"
        cmd = ["pkexec", "dnf", "copr", "remove", "-y", repo_slug]

        if output_cb:
            return self.run_streaming_command(cmd, output_cb)

        logger.info(f"Removing repo config: {repo_slug}")
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove repo {repo_slug}: {e}")
            return False

    # ------------------------------------------------------------------
    # Package management
    # ------------------------------------------------------------------

    def install_package(self, package_name: str, output_cb=None) -> bool:
        """Install a package using pkexec dnf install."""
        try:
            package_name = validate_package_name(package_name)
        except ValueError as e:
            logger.error(f"install_package validation error: {e}")
            return False

        cmd = ["pkexec", "dnf", "install", "-y", package_name]

        if output_cb:
            return self.run_streaming_command(cmd, output_cb)

        logger.info(f"Installing package: {package_name}")
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install package {package_name}: {e}")
            return False

    def remove_package(self, package_name: str, output_cb=None) -> bool:
        """Remove a package using pkexec dnf remove."""
        try:
            package_name = validate_package_name(package_name)
        except ValueError as e:
            logger.error(f"remove_package validation error: {e}")
            return False

        cmd = ["pkexec", "dnf", "remove", "-y", package_name]

        if output_cb:
            return self.run_streaming_command(cmd, output_cb)

        logger.info(f"Removing package: {package_name}")
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove package {package_name}: {e}")
            return False

    def is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed using rpm -q."""
        try:
            package_name = validate_package_name(package_name)
        except ValueError as e:
            logger.warning(f"is_package_installed validation error: {e}")
            return False

        cmd = ["rpm", "-q", "--", package_name]
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_packages(self, repo_id: str) -> List[str]:
        """
        List available packages in a repository using dnf repoquery.

        repo_id must be a validated 'copr:<host>:<owner>:<project>' string.
        The value is passed as a separate argument (not embedded in --repo=)
        to prevent option injection.
        """
        try:
            repo_id = validate_repo_id(repo_id)
        except ValueError as e:
            logger.error(f"list_packages validation error: {e}")
            return []

        # Pass --repo and repo_id as two separate list elements — never as
        # f"--repo={repo_id}" — to prevent option-injection via crafted IDs.
        cmd = [
            "dnf", "repoquery",
            "--repo", repo_id,
            "--available",
            "--queryformat", r"%{name}\n",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            packages = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    packages.append(line)
            return packages
        except subprocess.CalledProcessError:
            logger.error(f"Failed to list packages for {repo_id}")
            return []

    def is_repo_enabled(self, repo_id: str) -> bool:
        """Check whether a repo is enabled via dnf repolist."""
        cmd = ["dnf", "repolist", "enabled"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return repo_id in result.stdout
        except subprocess.CalledProcessError:
            return False

    def list_configured_coprs(self) -> List[Dict]:
        """
        List all configured COPR repositories using `dnf copr list`.

        Each entry from the command is parsed and validated: any line whose
        host, owner, or project component fails the allowlist check is
        silently skipped with a warning logged.
        """
        cmd = ["dnf", "copr", "list"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list enabled coprs: {e}")
            return []

        repos = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            is_enabled = True
            if line.endswith(" (disabled)"):
                is_enabled = False
                line = line[: -len(" (disabled)")]

            # Strip any trailing tags (e.g., [eternal_deps])
            line = line.split(" ")[0]

            parts = line.split("/")
            if len(parts) < 3:
                logger.debug(f"Skipping unrecognised copr list line: {raw_line!r}")
                continue

            host = parts[0]
            owner = parts[-2]
            project = parts[-1]

            # Validate each component before using it in any command.
            try:
                host = validate_host(host)
                owner = validate_owner(owner)
                project = validate_project(project)
            except ValueError as e:
                logger.warning(
                    f"Skipping repo with invalid component ({e}): {raw_line!r}"
                )
                continue

            full_name = f"{owner}/{project}"
            repo_id = f"copr:{host}:{owner}:{project}"

            repos.append(
                {
                    "full_name": full_name,
                    "description": f"COPR Repository ({host})",
                    "owner": owner,
                    "project": project,
                    "id": repo_id,
                    "enabled": is_enabled,
                }
            )

        return repos
