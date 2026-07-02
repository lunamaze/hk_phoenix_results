import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

import psycopg2


def _to_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, float):
        return v
    if isinstance(v, int):
        return float(v)
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except Exception:
        return 0.0


def main() -> None:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    cur = conn.cursor()

    cur.execute("select player_id, nickname, player_id_new from player_mapping order by player_id")
    player_mapping = [{"player_id": r[0], "nickname": r[1], "player_id_new": r[2]} for r in cur.fetchall()]

    cur.execute(
        """
        select
          year, phase, round_name, table_name, match_no,
          e_player_id, e_score, e_penalty,
          e_rank,
          s_player_id, s_score, s_penalty,
          s_rank,
          w_player_id, w_score, w_penalty,
          w_rank,
          n_player_id, n_score, n_penalty
          ,n_rank
        from match_result
        order by year, phase, round_name, table_name, match_no, id
        """
    )
    matches: List[Dict[str, Any]] = []
    years_set = set()
    for r in cur.fetchall():
        (
            year,
            phase,
            round_name,
            table_name,
            match_no,
            e_player_id,
            e_score,
            e_penalty,
            e_rank,
            s_player_id,
            s_score,
            s_penalty,
            s_rank,
            w_player_id,
            w_score,
            w_penalty,
            w_rank,
            n_player_id,
            n_score,
            n_penalty,
            n_rank,
        ) = r
        years_set.add(int(year))
        matches.append(
            {
                "year": int(year),
                "phase": phase,
                "round_name": round_name,
                "table_name": table_name,
                "match_no": int(match_no),
                "e_player_id": e_player_id,
                "e_score": _to_float(e_score),
                "e_penalty": _to_float(e_penalty),
                "e_rank": int(e_rank),
                "s_player_id": s_player_id,
                "s_score": _to_float(s_score),
                "s_penalty": _to_float(s_penalty),
                "s_rank": int(s_rank),
                "w_player_id": w_player_id,
                "w_score": _to_float(w_score),
                "w_penalty": _to_float(w_penalty),
                "w_rank": int(w_rank),
                "n_player_id": n_player_id,
                "n_score": _to_float(n_score),
                "n_penalty": _to_float(n_penalty),
                "n_rank": int(n_rank),
            }
        )

    years = sorted(years_set)
    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "years": years,
        "player_mapping": player_mapping,
        "matches": matches,
    }

    out_path = "site/public/data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Wrote {out_path}")
    print(f"Years: {years}")
    print(f"Players: {len(player_mapping)}")
    print(f"Matches: {len(matches)}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
