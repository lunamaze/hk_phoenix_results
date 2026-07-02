import json
import os
import traceback
from typing import Any, Dict, List

import psycopg2


PHASE_REGULAR = "Regular"


def ensure_columns(cur) -> None:
    cur.execute("alter table match_result add column if not exists phase varchar(20) not null default %s", (PHASE_REGULAR,))
    cur.execute("alter table match_result add column if not exists e_rank integer")
    cur.execute("alter table match_result add column if not exists s_rank integer")
    cur.execute("alter table match_result add column if not exists w_rank integer")
    cur.execute("alter table match_result add column if not exists n_rank integer")


def main() -> None:
    src_path = os.getenv("SRC_JSON", "site/public/data.json")
    with open(src_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    player_mapping: List[Dict[str, Any]] = data.get("player_mapping", [])
    matches: List[Dict[str, Any]] = data.get("matches", [])

    conn = None
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        )
        cur = conn.cursor()

        ensure_columns(cur)

        for row in player_mapping:
            cur.execute(
                """
                insert into player_mapping (player_id, nickname)
                values (%s, %s)
                on conflict (player_id) do nothing
                """,
                (row["player_id"], row.get("nickname")),
            )

        cur.execute("truncate table match_result")

        cur.executemany(
            """
            insert into match_result (
              year, phase, round_name, table_name, match_no,
              e_player_id, e_score, e_penalty, e_rank,
              s_player_id, s_score, s_penalty, s_rank,
              w_player_id, w_score, w_penalty, w_rank,
              n_player_id, n_score, n_penalty, n_rank
            ) values (
              %(year)s, %(phase)s, %(round_name)s, %(table_name)s, %(match_no)s,
              %(e_player_id)s, %(e_score)s, %(e_penalty)s, %(e_rank)s,
              %(s_player_id)s, %(s_score)s, %(s_penalty)s, %(s_rank)s,
              %(w_player_id)s, %(w_score)s, %(w_penalty)s, %(w_rank)s,
              %(n_player_id)s, %(n_score)s, %(n_penalty)s, %(n_rank)s
            )
            """,
            [
                {
                    **m,
                    "phase": m.get("phase") or PHASE_REGULAR,
                }
                for m in matches
            ],
        )

        conn.commit()

        cur.execute("select year, phase, count(*) from match_result group by year, phase order by year, phase")
        print("rows_by_year_phase", cur.fetchall())

        cur.execute("select count(*) from match_result")
        print("total_rows", cur.fetchone()[0])

        cur.close()
        conn.close()
    except Exception:
        if conn:
            conn.rollback()
            conn.close()
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()

