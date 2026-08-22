from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def require_ephemeral_output(
    path: str | Path, *, github_actions: bool | None = None
) -> Path:
    """Reject persistent local generated-data paths.

    GitHub-hosted Actions workspaces are disposable. Outside Actions, generated
    data must stay below a system temporary directory so the repository cannot
    silently become a second persistent data store.
    """

    candidate = Path(path)
    in_github_actions = (
        os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
        if github_actions is None
        else github_actions
    )
    if in_github_actions:
        return candidate

    resolved = candidate.expanduser().resolve()
    temporary_roots = {
        Path(tempfile.gettempdir()).resolve(),
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
    }
    if any(_is_inside(resolved, root) for root in temporary_roots):
        return candidate

    raise RuntimeError(
        "persistent local generated-data output is disabled; use a system "
        "temporary directory or the GitHub Actions R2 pipeline"
    )
