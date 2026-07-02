import os
import re
from typing import Dict, List, Tuple

import psycopg2


PAT_OK = re.compile(r"^#\d{3}$")
PAT_NUM = re.compile(r"^#?\d+$")


def normalize_pid(pid: str) -> str:
    s = str(pid).strip()
    if s.startswith("#"):
        s = s[1:]
    s = re.sub(r"\D", "", s)
    if not s:
        return pid
    return f"#{int(s):03d}"


def load_distinct_ids(cur) -> Tuple[List[str], List[str]]:
    cur.execute("select distinct player_id from player_mapping order by player_id")
    pm = [r[0] for r in cur.fetchall()]

    cur.execute(
        """
        select distinct x
        from (
          select e_player_id as x from match_result
          union
          select s_player_id as x from match_result
          union
          select w_player_id as x from match_result
          union
          select n_player_id as x from match_result
        ) t
        order by x
        """
    )
    mr = [r[0] for r in cur.fetchall()]
    return pm, mr


def build_mapping(values: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if not PAT_NUM.match(s):
            continue
        new = normalize_pid(s)
        if s != new:
            mapping[s] = new
    return mapping


def main() -> None:
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "postgres")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")

    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    cur = conn.cursor()

    cur.execute("select current_database(), current_schema(), current_user")
    print("connected_to", cur.fetchone())

    pm_ids, mr_ids = load_distinct_ids(cur)
    pm_map = build_mapping(pm_ids)
    mr_map = build_mapping(mr_ids)

    all_map: Dict[str, str] = {}
    all_map.update(pm_map)
    all_map.update(mr_map)

    pm_whitespace = [x for x in pm_ids if x is not None and str(x) != str(x).strip()]
    mr_whitespace = [x for x in mr_ids if x is not None and str(x) != str(x).strip()]
    print("player_mapping_whitespace_ids", pm_whitespace)
    print("match_result_whitespace_ids", mr_whitespace)

    print("player_mapping_non3_ids", sorted(pm_map.items()))
    print("match_result_non3_ids", sorted(mr_map.items()))
    print("to_normalize_count", len(all_map))
    if not all_map:
        print("No non-3-digit numeric IDs found.")
        cur.close()
        conn.close()
        return

    cur.execute("begin")

    for old, new in all_map.items():
        cur.execute(
            """
            insert into player_mapping (player_id, nickname)
            select %s, nickname from player_mapping where player_id = %s
            on conflict (player_id) do nothing
            """,
            (new, old),
        )

    for col in ["e_player_id", "s_player_id", "w_player_id", "n_player_id"]:
        for old, new in all_map.items():
            cur.execute(
                f"update match_result set {col} = %s where {col} = %s",
                (new, old),
            )

    for old in all_map.keys():
        cur.execute("delete from player_mapping where player_id = %s", (old,))

    conn.commit()

    cur.execute("select year, count(*) from match_result group by year order by year")
    print("rows_by_year", cur.fetchall())

    cur.execute("select count(*) from player_mapping")
    print("player_mapping_total", cur.fetchone()[0])

    cur.execute(
        """
        select count(*)
        from player_mapping
        where player_id ~ '^#\\d{3}$'
        """
    )
    print("player_mapping_ok", cur.fetchone()[0])

    cur.execute(
        """
        select count(*)
        from (
          select e_player_id as x from match_result
          union
          select s_player_id as x from match_result
          union
          select w_player_id as x from match_result
          union
          select n_player_id as x from match_result
        ) t
        where x ~ '^#\\d{3}$'
        """
    )
    print("match_result_distinct_ok", cur.fetchone()[0])

    cur.execute(
        """
        select distinct x
        from (
          select e_player_id as x from match_result
          union
          select s_player_id as x from match_result
          union
          select w_player_id as x from match_result
          union
          select n_player_id as x from match_result
        ) t
        where x ~ '^#\\d+$' and x !~ '^#\\d{3}$'
        order by x
        """
    )
    leftovers = [r[0] for r in cur.fetchall()]
    print("match_result_leftover_non3", leftovers)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
