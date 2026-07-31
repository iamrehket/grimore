"""Import grim as a module, for pure helpers only.

Shared by stamp_spec and reconcile. Both scripts ask grim for judgment through
a subprocess; this is the other half, for the deterministic helpers where
shelling out would mean parsing a report to learn something grim can just tell
us. What must never come through here is a *rule*: phase A accumulated eleven
divergences by reimplementing grim's checks, and importing a rule to re-run it
locally is the same mistake with a shorter call stack.

The same resolved grim file backs both the import and the subprocess, so helper
semantics and lint semantics cannot come from different versions.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


class GrimImportError(Exception):
    """grim is missing, unreadable, or not the grim these scripts expect."""


def load_grim(grim_path: Path, required_api: tuple[str, ...]):
    if not grim_path.is_file():
        raise GrimImportError(f"grim not found at {grim_path}; pass --grim with its location")
    spec = importlib.util.spec_from_file_location("grim_for_finish_docs", grim_path)
    if spec is None or spec.loader is None:
        raise GrimImportError(f"cannot load grim from {grim_path}")
    module = importlib.util.module_from_spec(spec)
    # Importing grim would otherwise drop a __pycache__ into the target repo's
    # tools/ directory - an untracked artefact reconcile itself refuses on.
    sys.dont_write_bytecode = True
    # Registered BEFORE exec_module: @dataclass resolves the defining module
    # through sys.modules while the class body executes, and the import dies
    # inside the first dataclass without this.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - every import failure reports alike
        sys.modules.pop(spec.name, None)
        raise GrimImportError(f"could not import grim from {grim_path}: {exc}") from None
    missing = [name for name in required_api if not hasattr(module, name)]
    if missing:
        raise GrimImportError(
            f"grim at {grim_path} is missing {', '.join(missing)}; "
            f"it is too old or too new for this script"
        )
    return module
