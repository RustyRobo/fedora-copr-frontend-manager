# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026  elyssa
#
import logging
from typing import List, Dict, Optional

from backend.validation import validate_search_query

# Try to import the official copr library
try:
    import copr.v3
    HAS_COPR_LIB = True
except ImportError:
    HAS_COPR_LIB = False

logger = logging.getLogger(__name__)

_copr_client = None


def get_client():
    """Return a cached COPR API client, creating it on first call."""
    global _copr_client
    if _copr_client is None:
        if not HAS_COPR_LIB:
            raise RuntimeError("python3-copr library is not installed.")
        try:
            _copr_client = copr.v3.Client.create_from_config_file()
        except Exception:
            # Fall back to anonymous / unauthenticated client
            _copr_client = copr.v3.Client(
                {"copr_url": "https://copr.fedorainfracloud.org"}
            )
    return _copr_client


def search_copr(query: str) -> List[Dict]:
    """
    Search COPR repositories using the official `copr` Python library.

    Returns a list of dicts with keys:
        full_name, description, owner, project,
        homepage, instructions, contact, chroots, storage_usage
    """
    if not query:
        return []

    if not HAS_COPR_LIB:
        logger.error("python3-copr library not found.")
        return []

    # Validate and normalise the query before sending it to the API.
    try:
        query = validate_search_query(query)
    except ValueError as e:
        logger.warning(f"search_copr rejected query: {e}")
        return []

    try:
        client = get_client()
        result = client.project_proxy.search(query=query)

        projects = []
        for item in result:
            # Support both attribute-style objects and plain dicts.
            def _get(attr):
                val = getattr(item, attr, None)
                if val is None and isinstance(item, dict):
                    val = item.get(attr)
                return val

            owner   = _get("ownername")
            project = _get("name")
            desc    = _get("description")

            # Skip malformed entries that lack the mandatory fields.
            if not owner or not project:
                logger.debug(f"Skipping COPR result with missing owner/project: {item}")
                continue

            projects.append(
                {
                    "full_name":     f"{owner}/{project}",
                    "description":   desc or "",
                    "owner":         owner,
                    "project":       project,
                    "homepage":      _get("homepage"),
                    "instructions":  _get("instructions"),
                    "contact":       _get("contact"),
                    "chroots":       _get("chroot_repos"),
                    "storage_usage": _get("storage_usage"),
                }
            )

        return projects

    except copr.v3.exceptions.CoprNoResultException:
        # Expected: query returned zero results
        return []
    except copr.v3.exceptions.CoprException as e:
        logger.error(f"COPR API error during search: {e}")
        return []
    except Exception as e:
        # Catch-all for unexpected issues (network, parsing, etc.)
        logger.error(f"Unexpected error during COPR search: {e}")
        return []


def parse_search_html(html: str) -> List[Dict]:
    # Deprecated / unused
    return []
