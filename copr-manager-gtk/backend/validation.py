# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
"""
backend/validation.py — Input sanitization for all subprocess arguments.

All user-facing or API-sourced strings must pass through these validators
before being used in subprocess calls. Each function raises ValueError on
invalid input, which callers should catch and handle gracefully.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowlist regular expressions
# ---------------------------------------------------------------------------

# COPR owner names: optional leading @, then alphanumeric + dots/underscores/hyphens.
# Max 100 characters.
_OWNER_RE = re.compile(r'^@?[a-zA-Z0-9][a-zA-Z0-9._\-]{0,98}$')

# COPR project names: alphanumeric + dots/underscores/hyphens/plus.
# Max 100 characters.
_PROJECT_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._+\-]{0,98}$')

# RPM/DNF package names: alphanumeric + dots/underscores/hyphens/plus.
# Max 256 characters.
_PACKAGE_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._+\-]{0,254}$')

# Hostname component: alphanumeric + dots/hyphens (no wildcards, no slashes).
# Max 253 characters (DNS limit).
_HOST_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9.\-]{0,251}$')

# Search query: arbitrary printable text, but must not be empty or contain
# control characters / shell metacharacters that could confuse library calls.
_QUERY_RE = re.compile(r'^[\w\s._+\-@/]{1,200}$')

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_owner(owner: str) -> str:
    """
    Validate a COPR owner (user or group) name.

    Raises ValueError if invalid.
    Returns the owner string unchanged.
    """
    if not isinstance(owner, str) or not _OWNER_RE.match(owner):
        raise ValueError(f"Invalid COPR owner name: {owner!r}")
    return owner


def validate_project(project: str) -> str:
    """
    Validate a COPR project name.

    Raises ValueError if invalid.
    Returns the project string unchanged.
    """
    if not isinstance(project, str) or not _PROJECT_RE.match(project):
        raise ValueError(f"Invalid COPR project name: {project!r}")
    return project


def validate_package_name(name: str) -> str:
    """
    Validate an RPM/DNF package name.

    Raises ValueError if invalid.
    Returns the name unchanged.
    """
    if not isinstance(name, str) or not _PACKAGE_RE.match(name):
        raise ValueError(f"Invalid package name: {name!r}")
    return name


def validate_host(host: str) -> str:
    """
    Validate a hostname (used in repo IDs).

    Raises ValueError if invalid.
    Returns the host string unchanged.
    """
    if not isinstance(host, str) or not _HOST_RE.match(host):
        raise ValueError(f"Invalid hostname: {host!r}")
    return host


def validate_repo_id(repo_id: str) -> str:
    """
    Validate a fully-formed DNF/COPR repo ID of the form:
      copr:<host>:<owner>:<project>

    Raises ValueError if any component is invalid.
    Returns the repo_id string unchanged.
    """
    if not isinstance(repo_id, str):
        raise ValueError(f"repo_id must be a string, got {type(repo_id)}")

    parts = repo_id.split(':')
    if len(parts) != 4 or parts[0] != 'copr':
        raise ValueError(
            f"repo_id must be in the form 'copr:<host>:<owner>:<project>', got: {repo_id!r}"
        )

    _, host, owner, project = parts
    validate_host(host)
    validate_owner(owner)
    validate_project(project)
    return repo_id


def sanitize_full_name(full_name: str):
    """
    Split 'owner/project' and validate both components.

    Returns a (owner, project) tuple.
    Raises ValueError if the format is invalid or either component fails validation.
    """
    if not isinstance(full_name, str) or '/' not in full_name:
        raise ValueError(f"full_name must be 'owner/project', got: {full_name!r}")

    owner, project = full_name.split('/', 1)
    validate_owner(owner)
    validate_project(project)
    return owner, project


def validate_search_query(query: str) -> str:
    """
    Validate a COPR search query string.

    Raises ValueError if invalid.
    Returns the stripped query.
    """
    if not isinstance(query, str):
        raise ValueError("Search query must be a string.")
    query = query.strip()
    if not query:
        raise ValueError("Search query must not be empty.")
    if not _QUERY_RE.match(query):
        raise ValueError(f"Search query contains invalid characters: {query!r}")
    return query
