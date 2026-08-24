from __future__ import annotations

import re
from pathlib import Path

import olefile


ROOT = Path(r"C:\Users\w2982\Downloads\RCEP")


def read_text(path: Path) -> str:
    with olefile.OleFileIO(str(path)) as ole:
        data = ole.openstream("WordDocument").read()
    return data.decode("utf-16le", errors="ignore")


def clean(s: str) -> str:
    s = s.replace("\x07", " | ")
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t\xa0]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def around(text: str, pattern: str, radius: int = 900) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return ""
    return clean(text[max(0, m.start() - radius) : m.end() + radius])


def main() -> int:
    targets = []
    for path in sorted(ROOT.glob("*.doc")):
        text = read_text(path)
        if "8703" in text:
            targets.append((path, text))

    for path, text in targets:
        print("=" * 80)
        print(path.name.encode("unicode_escape").decode())
        print("-- start --")
        print(clean(text[:4000]).encode("unicode_escape").decode()[:2500])
        print("-- annex/appendix --")
        print(around(text, r"PHỤ LỤC|Phụ lục|BIỂU THUẾ|Biểu thuế", 1200).encode("unicode_escape").decode()[:3000])
        print("-- 8703.80.97 --")
        print(around(text, r"8703\.80\.97", 500).encode("unicode_escape").decode()[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
