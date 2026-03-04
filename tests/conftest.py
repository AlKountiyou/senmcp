from __future__ import annotations

import sys
from pathlib import Path


def _ensure_workspace_packages_on_path() -> None:
    """Add local workspace packages to sys.path for tests."""

    root = Path(__file__).resolve().parents[1]
    packages_dir = root / "packages"

    # Each workspace package has its own subdirectory under `packages/`.
    for package_name in ("mcp_core", "mcp_trust", "mcp_opendata", "mcp_services", "agent_app"):
        pkg_root = packages_dir / package_name
        if pkg_root.is_dir():
            pkg_root_str = str(pkg_root)
            if pkg_root_str not in sys.path:
                sys.path.insert(0, pkg_root_str)


_ensure_workspace_packages_on_path()

