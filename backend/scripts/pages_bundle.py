"""Zip the planner package, its data, and networkx (pure Python) for the in-browser demo (Pyodide).

    uv run python scripts/pages_bundle.py [output.zip]     # default: ../frontend/public/planner.zip

The browser gets the same code and the same networkx version the tests ran against. FastAPI and pydantic
come from Pyodide itself.
"""
import sys
import zipfile
from pathlib import Path

import networkx

BACKEND = Path(__file__).resolve().parents[1]
SKIP = {"__pycache__", "tests"}


def add_tree(z: zipfile.ZipFile, root: Path, prefix: str, suffixes: tuple[str, ...]) -> None:
    for f in sorted(root.rglob("*")):
        if f.is_file() and f.suffix in suffixes and not SKIP & set(f.relative_to(root).parts):
            z.write(f, f"{prefix}/{f.relative_to(root)}")


def build(out: Path) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        add_tree(z, BACKEND / "planner", "planner", (".py", ".json"))
        z.write(BACKEND / "data" / "sample_transcript.txt", "data/sample_transcript.txt")
        add_tree(z, Path(networkx.__file__).parent, "networkx", (".py",))
    return out.stat().st_size


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else BACKEND.parent / "frontend" / "public" / "planner.zip"
    print(f"{target} ({build(target) / 1e6:.1f} MB)")
