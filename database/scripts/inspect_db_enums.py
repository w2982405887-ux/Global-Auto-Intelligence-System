from __future__ import annotations

import os

from sqlalchemy import create_engine, text


def main() -> int:
    engine = create_engine(
        os.environ["GAIS_DATABASE_URL"],
        connect_args={"connect_timeout": 5},
    )
    with engine.connect() as conn:
        powertrains = [
            row[0]
            for row in conn.execute(
                text("select unnest(enum_range(NULL::ref.powertrain))::text")
            )
        ]
        origins = [
            row[0]
            for row in conn.execute(
                text("select unnest(enum_range(NULL::ref.origin_regime))::text")
            )
        ]
        agreements = [
            row[0]
            for row in conn.execute(
                text("select agreement_code from ref.trade_agreement order by agreement_code")
            )
        ]
    print("powertrain", powertrains)
    print("origin_regime", origins)
    print("agreements", agreements)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
