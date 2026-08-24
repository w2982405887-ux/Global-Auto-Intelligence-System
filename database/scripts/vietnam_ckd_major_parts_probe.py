from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    print(f"PROJECT_ROOT={PROJECT_ROOT}")
    print(f"EXISTS={PROJECT_ROOT.exists()}")
    for child in sorted(PROJECT_ROOT.iterdir()):
        print(child.name)


if __name__ == "__main__":
    main()
