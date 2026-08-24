from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python database/scripts/apply_sql_seed.py <seed.sql>")
        return 2

    database_url = os.environ.get("GAIS_DATABASE_URL")
    if not database_url:
        print("GAIS_DATABASE_URL is required")
        return 2

    seed_path = Path(sys.argv[1])
    sql = seed_path.read_text(encoding="utf-8")
    engine = create_engine(database_url)

    with engine.begin() as conn:
        conn.execute(text(sql))

    print(f"applied {seed_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
