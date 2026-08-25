from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python database/scripts/apply_sql_seed_from_env_file.py <seed.sql>", file=sys.stderr)
        return 2

    env = load_dotenv(PROJECT_ROOT / ".env")
    db_url = os.environ.get("GAIS_DATABASE_URL")
    if not db_url:
        db = env.get("POSTGRES_DB")
        user = env.get("POSTGRES_USER")
        password = env.get("POSTGRES_PASSWORD")
        host = env.get("POSTGRES_HOST", "127.0.0.1")
        port = env.get("POSTGRES_PORT", "5432")
        if not all([db, user, password, port]):
            print("GAIS_DATABASE_URL or POSTGRES_* values in .env are required", file=sys.stderr)
            return 2
        db_url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

    seed_path = Path(sys.argv[1])
    if not seed_path.is_absolute():
        seed_path = PROJECT_ROOT / seed_path
    sql = seed_path.read_text(encoding="utf-8")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text(sql))
    print(f"applied {seed_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
