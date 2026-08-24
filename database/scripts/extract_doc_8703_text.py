from __future__ import annotations

import re
import sys
from pathlib import Path


def ascii_strings(data: bytes, min_len: int = 4) -> list[str]:
    out: list[str] = []
    cur = bytearray()
    for b in data:
        if 32 <= b <= 126:
            cur.append(b)
        else:
            if len(cur) >= min_len:
                out.append(cur.decode("latin1", errors="ignore"))
            cur.clear()
    if len(cur) >= min_len:
        out.append(cur.decode("latin1", errors="ignore"))
    return out


def utf16le_strings(data: bytes, min_len: int = 4) -> list[str]:
    out: list[str] = []
    cur: list[int] = []
    for i in range(0, len(data) - 1, 2):
        code = data[i] | (data[i + 1] << 8)
        if code in (9, 10, 13) or 32 <= code <= 0xD7FF:
            cur.append(code)
        else:
            if len(cur) >= min_len:
                out.append("".join(chr(c) for c in cur))
            cur.clear()
    if len(cur) >= min_len:
        out.append("".join(chr(c) for c in cur))
    return out


def normalize(s: str) -> str:
    s = s.replace("\x00", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: python extract_doc_8703_text.py <out-dir> <doc> [<doc>...]")
        return 2

    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    for raw in sys.argv[2:]:
        path = Path(raw)
        data = path.read_bytes()
        strings = ascii_strings(data) + utf16le_strings(data)
        joined = normalize("\n".join(strings))
        hits = []
        for m in re.finditer(r"8703", joined):
            start = max(0, m.start() - 2500)
            end = min(len(joined), m.end() + 5000)
            hits.append(joined[start:end])
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem) + "_8703.txt"
        out_path = out_dir / safe_name
        out_path.write_text("\n\n--- HIT ---\n\n".join(hits), encoding="utf-8")
        print(f"{path.name.encode('unicode_escape').decode()} hits={len(hits)} out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
