import os
from typing import Any, Dict, List, Tuple


def _pid_from_member_no(no: int) -> str:
    return f"#{int(no):03d}"


def _normalize_name(name: str) -> str:
    return " ".join(str(name).strip().split())


def _normalize_key(name: str) -> str:
    s = _normalize_name(name).casefold()
    s = s.replace(".", "").replace("_", "").replace("-", "")
    s = s.replace(" ", "")
    if s in {"is2", "ls2"}:
        return "ls2"
    if s in {"bee"}:
        return "bee"
    return s


PLAYER_BY_NAME_2021: Dict[str, str] = {
    _normalize_key("Gary"): "#044",
    _normalize_key("ls2"): "#029",
    _normalize_key("Ls2"): "#029",
    _normalize_key("Is2"): "#029",
    _normalize_key("Puyo"): "#052",
    _normalize_key("Kelvin"): "#214",
    _normalize_key("BEE"): "#216",
    _normalize_key("Bee"): "#216",
    _normalize_key("Ben"): "#067",
    _normalize_key("JIM"): "#215",
    _normalize_key("Peter"): "#028",
    _normalize_key("Desmond"): "#032",
    _normalize_key("Sam Yip"): "#081",
    _normalize_key("七月"): "#003",
    _normalize_key("業"): "#021",
    _normalize_key("Ho"): "#053",
}


def _resolve_player_id(name_or_id: str) -> str:
    s = str(name_or_id).strip()
    if s.startswith("#"):
        return s if len(s) == 4 else f"#{int(s.replace('#', '')):03d}"
    key = _normalize_key(s)
    pid = PLAYER_BY_NAME_2021.get(key)
    if not pid:
        raise ValueError(f"Unresolved player name: {name_or_id}")
    return pid


def get_2021_player_mapping_id_to_nickname() -> Dict[str, str]:
    return {
        "#044": "Gary",
        "#029": "Ls2",
        "#052": "Puyo",
        "#214": "Kelvin",
        "#216": "BEE",
        "#067": "Ben",
        "#215": "JIM",
        "#028": "Peter",
        "#021": "業",
        "#003": "七月",
        "#032": "Desmond",
        "#081": "Sam Yip",
    }


def get_2021_table_matches() -> Dict[int, Dict[str, List[Tuple[str, List[float]]]]]:
    return {
        1: {
            "A": [
                ("Is2", [53.7, 69.7, 56.5, -23.7]),
                ("七月", [4.7, -24.2, 12.9, 57.8]),
                ("Gary", [-16.1, 9.3, -58.8, -51.8]),
                ("Desmond", [-42.3, -54.8, -10.6, 17.7]),
            ],
            "B": [
                ("Ben", [52.4, 2.6, -56.4, -20.1]),
                ("JIM", [5.6, -20.8, -32.4, -47.0]),
                ("Peter", [-15.9, 74.0, 68.7, 64.4]),
                ("Kelvin", [-42.1, -55.8, 20.1, 2.7]),
            ],
            "C": [
                ("Puyo", [60.8, -39.1, -0.2, -53.7]),
                ("Bee", [19.3, -16.8, -26.3, -28.2]),
                ("Sam Yip", [-21.8, 51.0, 74.2, 71.0]),
                ("業", [-58.3, 4.9, -47.7, 10.9]),
            ],
        },
        2: {
            "A": [
                ("Puyo", [68.3, -25.8, 9.4, -20.9]),
                ("Desmond", [-24.4, 66.8, -20.9, 12.7]),
                ("Kelvin", [-44.5, 5.0, 55.1, -66.4]),
                ("Ben", [0.6, -46.0, -43.6, 74.6]),
            ],
            "B": [
                ("七月", [-34.3, 65.1, -40.7, -27.6]),
                ("JIM", [15.5, -52.9, -18.3, 67.8]),
                ("Gary", [-62.0, 5.3, 7.1, -54.2]),
                ("Bee", [80.8, -17.5, 51.9, 14.0]),
            ],
            "C": [
                ("Peter", [58.0, 1.0, 55.5, -24.6]),
                ("業", [11.6, -20.6, -50.3, 84.2]),
                ("LS2", [-54.8, 68.1, 14.2, -85.2]),
                ("Sam Yip", [-14.8, -48.5, -19.4, 25.6]),
            ],
        },
        3: {
            "A": [
                (_pid_from_member_no(32), [9.3, 99.7, 61.2, -41.9]),
                (_pid_from_member_no(216), [-50.7, -8.1, -50.4, 10.2]),
                (_pid_from_member_no(67), [58.1, -31.3, -17.7, 52.0]),
                (_pid_from_member_no(81), [-16.7, -60.3, 6.9, -20.3]),
            ],
            "B": [
                (_pid_from_member_no(52), [70.5, -26.5, 11.9, -45.8]),
                (_pid_from_member_no(29), [1.6, -56.6, -26.6, 51.0]),
                (_pid_from_member_no(3), [-23.3, 74.6, -58.7, 10.8]),
                (_pid_from_member_no(215), [-48.8, 8.5, 73.4, -16.0]),
            ],
            "C": [
                (_pid_from_member_no(214), [4.1, 6.1, 9.4, -64.9]),
                (_pid_from_member_no(28), [59.1, -14.7, -44.5, -28.0]),
                (_pid_from_member_no(44), [-19.7, 49.3, 54.1, 20.9]),
                (_pid_from_member_no(21), [-43.5, -40.7, -19.0, 72.0]),
            ],
        },
        4: {
            "A": [
                (_pid_from_member_no(52), [50.3, 12.3, -21.9, -42.9]),
                (_pid_from_member_no(28), [-15.4, -19.6, -52.9, 64.4]),
                (_pid_from_member_no(29), [8.9, 54.9, 72.2, -21.7]),
                (_pid_from_member_no(67), [-43.8, -47.6, 2.6, 0.2]),
            ],
            "B": [
                (_pid_from_member_no(32), [52.9, 72.2, -31.0, 55.0]),
                (_pid_from_member_no(215), [6.9, -28.1, -31.0, -18.7]),
                (_pid_from_member_no(216), [-14.0, -55.2, -0.6, 11.3]),
                (_pid_from_member_no(21), [-45.8, 11.1, 62.6, -47.6]),
            ],
            "C": [
                (_pid_from_member_no(214), [69.0, -19.3, 64.3, -5.3]),
                (_pid_from_member_no(81), [10.6, 55.0, -12.9, 17.7]),
                (_pid_from_member_no(44), [-26.4, -49.6, -68.8, 60.9]),
                (_pid_from_member_no(3), [-53.2, 13.9, 17.4, -73.3]),
            ],
        },
        5: {
            "A": [
                (_pid_from_member_no(67), [-27.7, -62.3, 61.0, -59.9]),
                (_pid_from_member_no(29), [63.2, 16.1, -16.3, 19.4]),
                (_pid_from_member_no(44), [17.7, 59.9, 7.8, -28.7]),
                (_pid_from_member_no(216), [-53.2, -13.7, -52.5, 69.2]),
            ],
            "B": [
                (_pid_from_member_no(214), [60.9, 5.3, -64.9, 64.7]),
                (_pid_from_member_no(215), [-50.1, -21.7, 2.1, -49.2]),
                (_pid_from_member_no(3), [-15.5, -45.9, -42.5, -19.8]),
                (_pid_from_member_no(21), [4.7, 62.3, 105.3, 4.3]),
            ],
            "C": [
                (_pid_from_member_no(28), [10.4, 66.0, 58.6, 70.7]),
                (_pid_from_member_no(32), [-26.5, 8.0, 12.0, 6.1]),
                (_pid_from_member_no(52), [-47.3, -48.4, -20.4, -58.7]),
                (_pid_from_member_no(81), [63.4, -25.6, -50.2, -18.1]),
            ],
        },
        6: {
            "A": [
                (_pid_from_member_no(44), [56.1, -72.8, 65.1, -14.4]),
                (_pid_from_member_no(52), [14.3, 77.3, -57.0, 6.5]),
                (_pid_from_member_no(81), [-21.0, 12.4, -18.0, 60.6]),
                (_pid_from_member_no(215), [-49.4, -16.9, 9.9, -52.7]),
            ],
            "B": [
                (_pid_from_member_no(29), [47.6, 80.3, -56.0, -22.4]),
                (_pid_from_member_no(32), [7.5, -58.9, -20.4, 4.6]),
                (_pid_from_member_no(214), [-14.2, 15.4, 72.4, -42.8]),
                (_pid_from_member_no(216), [-40.9, -36.8, 4.0, 60.6]),
            ],
            "C": [
                (_pid_from_member_no(3), [70.1, -38.9, -24.2, 76.3]),
                (_pid_from_member_no(67), [12.8, -17.1, 2.9, 19.5]),
                (_pid_from_member_no(28), [-14.4, 50.7, -45.4, -36.0]),
                (_pid_from_member_no(21), [-68.5, 5.3, 66.7, -59.8]),
            ],
        },
        7: {
            "A": [
                (_pid_from_member_no(3), [61.1, 11.9, 54.8, -76.5]),
                (_pid_from_member_no(52), [3.7, -52.7, -46.2, 21.8]),
                (_pid_from_member_no(216), [-22.0, -13.2, -16.3, 67.3]),
                (_pid_from_member_no(28), [-42.8, 54.0, 7.7, -12.6]),
            ],
            "B": [
                (_pid_from_member_no(32), [-12.0, 7.8, -9.6, -67.2]),
                (_pid_from_member_no(29), [-48.9, -47.4, -35.0, 84.8]),
                (_pid_from_member_no(67), [52.1, 59.8, 100.2, -8.8]),
                (_pid_from_member_no(215), [8.8, -20.2, -55.6, -8.8]),
            ],
            "C": [
                (_pid_from_member_no(81), [-24.0, 22.5, -69.7, -63.7]),
                (_pid_from_member_no(44), [59.6, -1.1, 78.0, 72.0]),
                (_pid_from_member_no(21), [12.4, 95.1, 9.9, -18.0]),
                (_pid_from_member_no(214), [-48.0, -116.5, -18.2, 9.7]),
            ],
        },
        8: {
            "A": [
                (_pid_from_member_no(28), [35.4, 10.3, 10.9, 67.2]),
                (_pid_from_member_no(215), [35.4, 52.4, -46.3, -63.3]),
                (_pid_from_member_no(32), [-16.2, -10.3, 54.2, 23.6]),
                (_pid_from_member_no(44), [-54.6, -52.4, -18.8, -27.5]),
            ],
            "B": [
                (_pid_from_member_no(29), [-51.7, 72.1, 4.4, 67.1]),
                (_pid_from_member_no(21), [-20.7, 0.6, -40.1, 6.0]),
                (_pid_from_member_no(52), [14.9, -22.9, -16.8, -14.1]),
                (_pid_from_member_no(216), [57.5, -49.8, 52.5, -59.0]),
            ],
            "C": [
                (_pid_from_member_no(214), [74.8, -48.4, -56.7, -63.0]),
                (_pid_from_member_no(3), [-23.0, 15.2, 19.2, -17.9]),
                (_pid_from_member_no(81), [-54.3, -24.0, -27.6, 14.4]),
                (_pid_from_member_no(67), [2.5, 57.2, 65.1, 66.5]),
            ],
        },
        9: {
            "A": [
                (_pid_from_member_no(214), [-43.3, 6.0, -46.0, 15.7]),
                (_pid_from_member_no(28), [4.1, 54.4, -20.8, -18.2]),
                (_pid_from_member_no(52), [-17.8, -40.5, 56.5, 59.2]),
                (_pid_from_member_no(216), [57.0, -19.9, 10.3, -56.7]),
            ],
            "B": [
                (_pid_from_member_no(215), [5.4, 18.5, -54.4, 3.2]),
                (_pid_from_member_no(3), [66.6, 68.4, -20.3, 41.6]),
                (_pid_from_member_no(29), [-51.6, -65.7, 6.6, -21.7]),
                (_pid_from_member_no(81), [-20.4, -21.2, 68.1, -43.1]),
            ],
            "C": [
                (_pid_from_member_no(21), [15.7, 77.9, -52.0, -61.3]),
                (_pid_from_member_no(67), [69.3, -50.6, 59.6, 16.4]),
                (_pid_from_member_no(32), [-69.1, 2.5, -17.6, 66.3]),
                (_pid_from_member_no(44), [-15.9, -29.8, 10.0, -21.4]),
            ],
        },
        10: {
            "A": [
                (_pid_from_member_no(28), [3.4, -20.0, 6.5, 15.4]),
                (_pid_from_member_no(32), [78.8, 10.1, -48.1, -39.4]),
                (_pid_from_member_no(3), [-64.7, -89.7, 68.1, -60.7]),
                (_pid_from_member_no(216), [-17.5, 99.6, -26.5, 84.7]),
            ],
            "B": [
                (_pid_from_member_no(52), [12.2, -44.0, -6.2, -16.1]),
                (_pid_from_member_no(67), [53.1, -23.2, 55.8, 7.9]),
                (_pid_from_member_no(21), [-56.1, 62.7, -43.4, 56.7]),
                (_pid_from_member_no(44), [-9.2, 4.5, -6.2, -48.5]),
            ],
            "C": [
                (_pid_from_member_no(29), [-22.4, 23.4, 16.5, -30.9]),
                (_pid_from_member_no(214), [57.2, -24.7, -68.0, -5.5]),
                (_pid_from_member_no(215), [8.8, 65.0, -18.1, 87.5]),
                (_pid_from_member_no(81), [-43.6, -63.7, 69.6, -51.1]),
            ],
        },
        11: {
            "A": [
                (_pid_from_member_no(32), [-11.7, -15.3, -33.7, -14.0]),
                (_pid_from_member_no(21), [57.9, 52.7, 77.0, 64.4]),
                (_pid_from_member_no(52), [-54.6, -48.5, 11.0, -64.1]),
                (_pid_from_member_no(214), [8.4, 11.1, -54.3, 13.7]),
            ],
            "B": [
                (_pid_from_member_no(67), [-44.2, -23.3, -28.3, -18.5]),
                (_pid_from_member_no(216), [57.9, -65.3, 77.2, 53.1]),
                (_pid_from_member_no(81), [9.3, 15.3, -52.6, -42.0]),
                (_pid_from_member_no(215), [-23.0, 73.3, 3.7, 7.4]),
            ],
            "C": [
                (_pid_from_member_no(28), [10.6, -23.5, 4.2, 82.2]),
                (_pid_from_member_no(29), [-48.0, -54.7, -41.6, -23.3]),
                (_pid_from_member_no(44), [-17.7, 10.1, -16.8, 16.1]),
                (_pid_from_member_no(3), [55.1, 68.1, 54.2, -75.0]),
            ],
        },
        12: {
            "A": [
                (_pid_from_member_no(44), [-18.9, 75.3, 64.3, 63.0]),
                (_pid_from_member_no(29), [-43.1, -20.2, 4.2, -69.2]),
                (_pid_from_member_no(52), [4.7, 2.0, -21.6, 15.2]),
                (_pid_from_member_no(214), [57.3, -57.1, -46.9, -9.0]),
            ],
            "B": [
                (_pid_from_member_no(216), [11.9, -51.2, -18.2, -19.2]),
                (_pid_from_member_no(67), [-52.9, -20.1, -55.2, -46.2]),
                (_pid_from_member_no(215), [-25.4, 66.2, 70.3, 55.4]),
                (_pid_from_member_no(28), [66.4, 5.1, 3.1, 10.0]),
            ],
            "C": [
                (_pid_from_member_no(21), [-26.2, -10.9, -15.8, -65.5]),
                (_pid_from_member_no(3), [66.8, -10.9, 10.7, 11.5]),
                (_pid_from_member_no(32), [-48.6, -50.0, -62.2, -37.6]),
                (_pid_from_member_no(81), [8.0, 71.8, 67.3, 91.6]),
            ],
        },
    }


def build_2021_match_rows() -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    tables = get_2021_table_matches()

    def ranks(scores: List[float]) -> List[int]:
        out: List[int] = []
        for i, si in enumerate(scores):
            better = 0
            for j, sj in enumerate(scores):
                if i == j:
                    continue
                if sj > si:
                    better += 1
            out.append(1 + better)
        return out

    for round_no in sorted(tables.keys()):
        for table_letter, rows in tables[round_no].items():
            if len(rows) != 4:
                raise ValueError(f"Round {round_no} Table {table_letter}: expected 4 players")
            for _, match_scores in rows:
                if len(match_scores) != 4:
                    raise ValueError(f"Round {round_no} Table {table_letter}: expected 4 match scores")

            player_ids = [_resolve_player_id(n) for n, _ in rows]
            for match_no in range(1, 5):
                m_scores = [float(scores[match_no - 1]) for _, scores in rows]
                m_ranks = ranks(m_scores)
                data.append(
                    {
                        "year": 2021,
                        "phase": "Regular",
                        "round_name": f"Round {round_no}",
                        "table_name": f"{round_no}{table_letter}",
                        "match_no": match_no,
                        "e_player_id": player_ids[0],
                        "e_score": m_scores[0],
                        "e_penalty": 0.0,
                        "e_rank": m_ranks[0],
                        "s_player_id": player_ids[1],
                        "s_score": m_scores[1],
                        "s_penalty": 0.0,
                        "s_rank": m_ranks[1],
                        "w_player_id": player_ids[2],
                        "w_score": m_scores[2],
                        "w_penalty": 0.0,
                        "w_rank": m_ranks[2],
                        "n_player_id": player_ids[3],
                        "n_score": m_scores[3],
                        "n_penalty": 0.0,
                        "n_rank": m_ranks[3],
                    }
                )
    return data


def write_sql(out_path: str) -> None:
    match_rows = build_2021_match_rows()
    player_map = get_2021_player_mapping_id_to_nickname()

    def q(s: Any) -> str:
        return "'" + str(s).replace("'", "''") + "'"

    stmts: List[str] = []

    stmts.append("BEGIN;")
    stmts.append("DELETE FROM match_result WHERE year = 2021;")

    for pid, nickname in player_map.items():
        stmts.append(
            f"INSERT INTO player_mapping (player_id, nickname) VALUES ({q(pid)}, {q(nickname)}) "
            "ON CONFLICT (player_id) DO NOTHING;"
        )

    for r in match_rows:
        stmts.append(
            "INSERT INTO match_result (year, phase, round_name, table_name, match_no, "
            "e_player_id, e_score, e_penalty, e_rank, s_player_id, s_score, s_penalty, s_rank, "
            "w_player_id, w_score, w_penalty, w_rank, n_player_id, n_score, n_penalty, n_rank) VALUES ("
            f"{int(r['year'])}, {q(r['phase'])}, {q(r['round_name'])}, {q(r['table_name'])}, {int(r['match_no'])}, "
            f"{q(r['e_player_id'])}, {float(r['e_score'])}, {float(r['e_penalty'])}, {int(r['e_rank'])}, "
            f"{q(r['s_player_id'])}, {float(r['s_score'])}, {float(r['s_penalty'])}, {int(r['s_rank'])}, "
            f"{q(r['w_player_id'])}, {float(r['w_score'])}, {float(r['w_penalty'])}, {int(r['w_rank'])}, "
            f"{q(r['n_player_id'])}, {float(r['n_score'])}, {float(r['n_penalty'])}, {int(r['n_rank'])}"
            ");"
        )

    stmts.append("COMMIT;")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(stmts))


def main():
    out_path = os.getenv("OUT_SQL", "migration_2021_photos.sql")
    write_sql(out_path)
    print(f"Wrote {out_path}")
    rows = build_2021_match_rows()
    print(f"Match rows: {len(rows)}")


if __name__ == "__main__":
    main()
