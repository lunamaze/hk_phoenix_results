import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psycopg2


PHASE_REGULAR = "Regular"


def ensure_tables(cur) -> None:
    cur.execute(
        """
        create table if not exists player_mapping (
          id serial primary key,
          player_id varchar(50) unique not null,
          nickname varchar(100),
          created_at timestamp default current_timestamp
        )
        """
    )
    cur.execute("alter table player_mapping add column if not exists player_id_new varchar(50)")

    cur.execute(
        """
        do $$
        begin
          if not exists (
            select 1
            from pg_constraint
            where conname = 'player_mapping_player_id_new_uniq'
          ) then
            alter table player_mapping
            add constraint player_mapping_player_id_new_uniq unique (player_id_new);
          end if;
        end $$;
        """
    )

    cur.execute(
        """
        create table if not exists match_result (
          id serial primary key,
          year integer not null,
          phase varchar(20) not null default 'Regular',
          round_name varchar(50),
          table_name varchar(50),
          match_no integer,
          e_player_id varchar(50),
          e_score decimal(10,2),
          e_penalty decimal(10,2) default 0,
          e_rank integer,
          s_player_id varchar(50),
          s_score decimal(10,2),
          s_penalty decimal(10,2) default 0,
          s_rank integer,
          w_player_id varchar(50),
          w_score decimal(10,2),
          w_penalty decimal(10,2) default 0,
          w_rank integer,
          n_player_id varchar(50),
          n_score decimal(10,2),
          n_penalty decimal(10,2) default 0,
          n_rank integer,
          created_at timestamp default current_timestamp
        )
        """
    )

    cur.execute("alter table match_result add column if not exists phase varchar(20) not null default %s", (PHASE_REGULAR,))
    cur.execute("alter table match_result add column if not exists e_rank integer")
    cur.execute("alter table match_result add column if not exists s_rank integer")
    cur.execute("alter table match_result add column if not exists w_rank integer")
    cur.execute("alter table match_result add column if not exists n_rank integer")


def load_snapshot(snapshot_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    with snapshot_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    player_mapping: List[Dict[str, Any]] = data.get("player_mapping", [])
    matches: List[Dict[str, Any]] = data.get("matches", [])
    return player_mapping, matches


def main() -> None:
    src_json = os.getenv("SRC_JSON")
    if src_json:
        snapshot_path = Path(src_json)
    else:
        candidates = [
            Path("site") / "public" / "data.json",
            Path("docs") / "public" / "data.json",
        ]
        snapshot_path = next((p for p in candidates if p.exists()), candidates[0])

    year_from = int(os.getenv("YEAR_FROM", "2021"))
    year_to = int(os.getenv("YEAR_TO", "2025"))

    player_mapping, matches = load_snapshot(snapshot_path)
    matches_2021_2025 = [m for m in matches if year_from <= int(m.get("year", 0) or 0) <= year_to]

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    cur = conn.cursor()

    ensure_tables(cur)

    for row in player_mapping:
        cur.execute(
            """
            insert into player_mapping (player_id, nickname, player_id_new)
            values (%s, %s, %s)
            on conflict (player_id) do update set
              nickname = excluded.nickname,
              player_id_new = excluded.player_id_new
            """,
            (row["player_id"], row.get("nickname"), row.get("player_id_new")),
        )

    cur.execute("delete from match_result where year between %s and %s", (year_from, year_to))

    if matches_2021_2025:
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
            [{**m, "phase": m.get("phase") or PHASE_REGULAR} for m in matches_2021_2025],
        )

    conn.commit()

    cur.execute(
        "select year, phase, count(*) from match_result where year between %s and %s group by year, phase order by year, phase",
        (year_from, year_to),
    )
    print("rows_by_year_phase", cur.fetchall())
    cur.execute("select count(*) from match_result where year between %s and %s", (year_from, year_to))
    print("total_rows_2021_2025", cur.fetchone()[0])
    cur.execute("select count(*) from player_mapping")
    print("player_mapping_rows", cur.fetchone()[0])

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

