import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import psycopg2


PHASE_REGULAR = "Regular"
PHASE_SEMI = "Semi-Final"
PHASE_FINAL = "Final"


@dataclass(frozen=True)
class MatchRow:
    year: int
    phase: str
    round_name: str
    table_name: str
    match_no: int
    e_player_id: str
    e_score: float
    e_penalty: float
    e_rank: int
    s_player_id: str
    s_score: float
    s_penalty: float
    s_rank: int
    w_player_id: str
    w_score: float
    w_penalty: float
    w_rank: int
    n_player_id: str
    n_score: float
    n_penalty: float
    n_rank: int


def normalize_pid(pid: Any) -> str:
    s = str(pid).strip()
    if s.startswith("#"):
        s = s[1:]
    s = re.sub(r"\D", "", s)
    return f"#{int(s):03d}"


def normalize_name_key(name: Any) -> str:
    s = str(name).strip()
    s = " ".join(s.split())
    s = s.casefold()
    s = re.sub(r"[\s._-]+", "", s)
    return s


def build_name_to_id(mapping: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name, pid in mapping.items():
        out[normalize_name_key(name)] = normalize_pid(pid)
    return out


def load_player_mapping_from_seating16(xl: pd.ExcelFile) -> Dict[str, str]:
    if "Seating-16" not in xl.sheet_names:
        return {}
    df = pd.read_excel(xl, sheet_name="Seating-16", header=None)

    mapping: Dict[str, str] = {}

    def harvest_section(header_row_idx: int, id_col: int, name_col: int) -> None:
        for r in range(header_row_idx + 1, len(df)):
            mjbs_id = df.iat[r, id_col] if id_col < df.shape[1] else None
            name = df.iat[r, name_col] if name_col < df.shape[1] else None
            if pd.isna(mjbs_id) and pd.isna(name):
                continue
            if pd.isna(mjbs_id) or pd.isna(name):
                continue
            mjbs_id_s = str(mjbs_id).strip()
            name_s = str(name).strip()
            if not mjbs_id_s.startswith("#"):
                continue
            mapping[name_s] = mjbs_id_s

    for r in range(len(df)):
        row = [df.iat[r, c] for c in range(min(df.shape[1], 60))]
        for c, v in enumerate(row):
            if pd.isna(v):
                continue
            v_s = str(v).strip()
            if v_s == "MJBS-ID":
                id_col = c
                name_col = None
                for c2, v2 in enumerate(row):
                    if pd.isna(v2):
                        continue
                    if str(v2).strip() == "Name":
                        name_col = c2
                        break
                if name_col is not None:
                    harvest_section(r, id_col, name_col)
            if v_s in {"牌藝ID.", "牌藝ID"}:
                id_col = c
                name_col = None
                for c2, v2 in enumerate(row):
                    if pd.isna(v2):
                        continue
                    if str(v2).strip() in {"姓名", "Name"}:
                        name_col = c2
                        break
                if name_col is not None:
                    harvest_section(r, id_col, name_col)

    return mapping


def safe_float(v: Any) -> float:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def compute_ranks(e: float, s: float, w: float, n: float) -> Tuple[int, int, int, int]:
    scores = [e, s, w, n]
    ranks = []
    for i, si in enumerate(scores):
        better = 0
        for j, sj in enumerate(scores):
            if i == j:
                continue
            if sj > si:
                better += 1
        ranks.append(1 + better)
    return ranks[0], ranks[1], ranks[2], ranks[3]


def parse_eswn_sheet(
    xl: pd.ExcelFile,
    sheet_name: str,
    year: int,
    phase: str,
    name_to_id: Dict[str, str],
) -> List[MatchRow]:
    df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    out: List[MatchRow] = []

    def resolve_id(name: Any) -> str:
        key = normalize_name_key(name)
        pid = name_to_id.get(key)
        if pid:
            return pid
        raise ValueError(f"[{year} {sheet_name}] Unresolved name: {name}")

    for row_idx in range(len(df)):
        v = df.iat[row_idx, 0] if df.shape[1] > 0 else None
        if str(v).strip() != "E":
            continue
        header_row_idx = row_idx - 1 if row_idx - 1 >= 0 else None

        for col_start in range(1, df.shape[1], 4):
            if col_start + 3 >= df.shape[1]:
                break
            if header_row_idx is not None:
                header_val = df.iat[header_row_idx, col_start]
                if pd.isna(header_val) or str(header_val).strip() != "Player No":
                    continue

            table_name = None
            try:
                for back in range(1, 4):
                    if row_idx - back < 0:
                        break
                    maybe = df.iat[row_idx - back, col_start + 3]
                    if pd.notna(maybe) and str(maybe).strip():
                        table_name = str(maybe).strip()
                        break
            except Exception:
                table_name = None

            if not table_name:
                table_name = sheet_name

            names = [df.iat[row_idx + i, col_start] for i in range(4)]
            if any(pd.isna(n) for n in names):
                continue
            penalties = [df.iat[row_idx + i, col_start + 2] for i in range(4)]
            scores = [df.iat[row_idx + i, col_start + 3] for i in range(4)]

            pids = [resolve_id(n) for n in names]
            e_pid, s_pid, w_pid, n_pid = pids
            e_pen, s_pen, w_pen, n_pen = (safe_float(x) for x in penalties)
            e_sc, s_sc, w_sc, n_sc = (safe_float(x) for x in scores)
            e_rk, s_rk, w_rk, n_rk = compute_ranks(e_sc, s_sc, w_sc, n_sc)

            match_no = int(((col_start - 1) / 4) + 1)
            out.append(
                MatchRow(
                    year=year,
                    phase=phase,
                    round_name=sheet_name,
                    table_name=table_name,
                    match_no=match_no,
                    e_player_id=e_pid,
                    e_score=e_sc,
                    e_penalty=e_pen,
                    e_rank=e_rk,
                    s_player_id=s_pid,
                    s_score=s_sc,
                    s_penalty=s_pen,
                    s_rank=s_rk,
                    w_player_id=w_pid,
                    w_score=w_sc,
                    w_penalty=w_pen,
                    w_rank=w_rk,
                    n_player_id=n_pid,
                    n_score=n_sc,
                    n_penalty=n_pen,
                    n_rank=n_rk,
                )
            )

    return out


def parse_grid_sheet(
    xl: pd.ExcelFile,
    sheet_name: str,
    year: int,
    phase: str,
    round_label: str,
) -> Tuple[List[MatchRow], Dict[str, str]]:
    df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    out: List[MatchRow] = []
    pid_to_nick: Dict[str, str] = {}

    def find_in_row(r: int, target: str) -> Optional[int]:
        for c in range(df.shape[1]):
            v = df.iat[r, c]
            if pd.isna(v):
                continue
            if str(v).strip() == target:
                return c
        return None

    header_rows: List[int] = []
    for r in range(df.shape[0]):
        if find_in_row(r, "公司會員編號") is not None:
            header_rows.append(r)

    for hr in header_rows:
        id_col = find_in_row(hr, "公司會員編號")
        if id_col is None:
            continue
        first_col = find_in_row(hr, "第一局")
        second_col = find_in_row(hr, "第二局")
        third_col = find_in_row(hr, "第三局")
        fourth_col = find_in_row(hr, "第四局")
        if None in {first_col, second_col, third_col, fourth_col}:
            continue

        table_col = None
        table_letter = None
        for c in range(df.shape[1]):
            v = df.iat[hr, c]
            if pd.isna(v):
                continue
            s = str(v).strip()
            if s.endswith("桌") and len(s) <= 3:
                table_col = c
                table_letter = s.replace("桌", "")
                break

        if table_col is None:
            continue

        players = []
        for r in range(hr + 1, hr + 5):
            member_no = df.iat[r, id_col]
            name = df.iat[r, table_col]
            if pd.isna(member_no) or pd.isna(name):
                continue
            pid = normalize_pid(member_no)
            nick = str(name).strip()
            pid_to_nick[pid] = nick
            scores = [
                safe_float(df.iat[r, first_col]),
                safe_float(df.iat[r, second_col]),
                safe_float(df.iat[r, third_col]),
                safe_float(df.iat[r, fourth_col]),
            ]
            players.append((pid, scores))

        if len(players) != 4:
            continue

        table_name = f"{round_label}{table_letter}"
        for match_no in range(1, 5):
            e_pid, e_scores = players[0]
            s_pid, s_scores = players[1]
            w_pid, w_scores = players[2]
            n_pid, n_scores = players[3]
            e_sc = e_scores[match_no - 1]
            s_sc = s_scores[match_no - 1]
            w_sc = w_scores[match_no - 1]
            n_sc = n_scores[match_no - 1]
            e_rk, s_rk, w_rk, n_rk = compute_ranks(e_sc, s_sc, w_sc, n_sc)
            out.append(
                MatchRow(
                    year=year,
                    phase=phase,
                    round_name=round_label,
                    table_name=table_name,
                    match_no=match_no,
                    e_player_id=e_pid,
                    e_score=e_sc,
                    e_penalty=0.0,
                    e_rank=e_rk,
                    s_player_id=s_pid,
                    s_score=s_sc,
                    s_penalty=0.0,
                    s_rank=s_rk,
                    w_player_id=w_pid,
                    w_score=w_sc,
                    w_penalty=0.0,
                    w_rank=w_rk,
                    n_player_id=n_pid,
                    n_score=n_sc,
                    n_penalty=0.0,
                    n_rank=n_rk,
                )
            )

    return out, pid_to_nick


def extract_playoffs() -> Tuple[List[MatchRow], Dict[str, str]]:
    all_rows: List[MatchRow] = []
    pid_to_nick: Dict[str, str] = {}

    # 2025 / 2024: SF1-3 and F1-3 use E/S/W/N layout; ids via Seating-16 mapping
    for year, path in [(2025, "鳳凰位戰 2025 積分表及賽程.xlsx"), (2024, "鳳凰位戰 2024 積分表及賽程.xlsx")]:
        xl = pd.ExcelFile(path)
        mapping = load_player_mapping_from_seating16(xl)
        name_to_id = build_name_to_id(mapping)

        for s in ["SF1", "SF2", "SF3"]:
            if s in xl.sheet_names:
                all_rows.extend(parse_eswn_sheet(xl, s, year, PHASE_SEMI, name_to_id))
        for s in ["F1", "F2", "F3"]:
            if s in xl.sheet_names:
                all_rows.extend(parse_eswn_sheet(xl, s, year, PHASE_FINAL, name_to_id))

    # 2023: 複賽第1輪-3 => Semi-Final, 決賽第1輪-3 => Final
    xl_2023 = pd.ExcelFile("鳳凰位戰A League 2023積分表.xlsx")
    for i in [1, 2, 3]:
        semi_sheet = f"複賽第{i}輪"
        if semi_sheet in xl_2023.sheet_names:
            rows, m = parse_grid_sheet(xl_2023, semi_sheet, 2023, PHASE_SEMI, f"SF{i}")
            all_rows.extend(rows)
            pid_to_nick.update(m)
        final_sheet = f"決賽第{i}輪"
        if final_sheet in xl_2023.sheet_names:
            rows, m = parse_grid_sheet(xl_2023, final_sheet, 2023, PHASE_FINAL, f"F{i}")
            all_rows.extend(rows)
            pid_to_nick.update(m)

    # 2022: 複賽第1輪-3 => Semi-Final; 決賽 sheet has A/B/C blocks => Final 1/2/3
    xl_2022 = pd.ExcelFile("鳳凰位戰 2021-22 賽程及積分表 .xlsx")
    for i in [1, 2, 3]:
        semi_sheet = f"複賽第{i}輪"
        if semi_sheet in xl_2022.sheet_names:
            rows, m = parse_grid_sheet(xl_2022, semi_sheet, 2022, PHASE_SEMI, f"SF{i}")
            all_rows.extend(rows)
            pid_to_nick.update(m)

    if "決賽" in xl_2022.sheet_names:
        # Reuse grid parser but map A/B/C blocks into F1/F2/F3 by remapping round_label based on table letter
        df = pd.read_excel(xl_2022, sheet_name="決賽", header=None)

        def block_rows() -> List[Tuple[int, str]]:
            blocks: List[Tuple[int, str]] = []
            for r in range(df.shape[0]):
                if any((not pd.isna(df.iat[r, c]) and str(df.iat[r, c]).strip() == "公司會員編號") for c in range(df.shape[1])):
                    table_letter = None
                    for c in range(df.shape[1]):
                        v = df.iat[r, c]
                        if pd.isna(v):
                            continue
                        s = str(v).strip()
                        if s.endswith("桌") and len(s) <= 3:
                            table_letter = s.replace("桌", "")
                            break
                    if table_letter:
                        blocks.append((r, table_letter))
            return blocks

        blocks = block_rows()
        letter_to_round = {"A": "F1", "B": "F2", "C": "F3"}
        for hr, letter in blocks:
            round_label = letter_to_round.get(letter)
            if not round_label:
                continue
            # Build a temporary ExcelFile-like parsing by slicing, but easiest: write a small parser using the same logic as parse_grid_sheet.
            # Here we directly parse this header row and following 4 rows.
            def find_in_row(r: int, target: str) -> Optional[int]:
                for c in range(df.shape[1]):
                    v = df.iat[r, c]
                    if pd.isna(v):
                        continue
                    if str(v).strip() == target:
                        return c
                return None

            id_col = find_in_row(hr, "公司會員編號")
            first_col = find_in_row(hr, "第一局")
            second_col = find_in_row(hr, "第二局")
            third_col = find_in_row(hr, "第三局")
            fourth_col = find_in_row(hr, "第四局")
            table_col = None
            for c in range(df.shape[1]):
                v = df.iat[hr, c]
                if pd.isna(v):
                    continue
                s = str(v).strip()
                if s.endswith("桌") and len(s) <= 3:
                    table_col = c
                    break
            if None in {id_col, first_col, second_col, third_col, fourth_col, table_col}:
                continue

            players = []
            for r in range(hr + 1, hr + 5):
                member_no = df.iat[r, id_col]
                name = df.iat[r, table_col]
                if pd.isna(member_no) or pd.isna(name):
                    continue
                pid = normalize_pid(member_no)
                nick = str(name).strip()
                pid_to_nick[pid] = nick
                scores = [
                    safe_float(df.iat[r, first_col]),
                    safe_float(df.iat[r, second_col]),
                    safe_float(df.iat[r, third_col]),
                    safe_float(df.iat[r, fourth_col]),
                ]
                players.append((pid, scores))

            if len(players) != 4:
                continue

            table_name = f"{round_label}A"
            for match_no in range(1, 5):
                e_pid, e_scores = players[0]
                s_pid, s_scores = players[1]
                w_pid, w_scores = players[2]
                n_pid, n_scores = players[3]
                e_sc = e_scores[match_no - 1]
                s_sc = s_scores[match_no - 1]
                w_sc = w_scores[match_no - 1]
                n_sc = n_scores[match_no - 1]
                e_rk, s_rk, w_rk, n_rk = compute_ranks(e_sc, s_sc, w_sc, n_sc)
                all_rows.append(
                    MatchRow(
                        year=2022,
                        phase=PHASE_FINAL,
                        round_name=round_label,
                        table_name=table_name,
                        match_no=match_no,
                        e_player_id=e_pid,
                        e_score=e_sc,
                        e_penalty=0.0,
                        e_rank=e_rk,
                        s_player_id=s_pid,
                        s_score=s_sc,
                        s_penalty=0.0,
                        s_rank=s_rk,
                        w_player_id=w_pid,
                        w_score=w_sc,
                        w_penalty=0.0,
                        w_rank=w_rk,
                        n_player_id=n_pid,
                        n_score=n_sc,
                        n_penalty=0.0,
                        n_rank=n_rk,
                    )
                )

    pid_to_nick.setdefault("#028", "Peter")
    pid_to_nick.setdefault("#021", "業")
    pid_to_nick.setdefault("#067", "Ben")
    pid_to_nick.setdefault("#003", "七月")

    final_2021_peter = [
        [-62.6, -19.1, -19.9, 56.4],
        [67.6, -24.2, -18.6, -48.3],
        [64.4, 10.0, 4.3, -13.9],
    ]
    final_2021_ye = [
        [-3.0, 8.5, 14.7, -17.9],
        [-69.8, 60.9, -60.2, 8.2],
        [-49.3, -11.8, 57.0, -49.3],
    ]
    final_2021_ben = [
        [-28.6, -76.2, -58.0, 10.2],
        [15.8, 11.8, 12.0, -19.6],
        [-21.5, -49.2, -45.4, 9.4],
    ]
    final_2021_july = [
        [94.2, 86.8, 63.2, -48.7],
        [-13.6, -48.5, 66.8, 59.7],
        [6.4, 51.0, -15.9, 53.8],
    ]

    for round_idx in range(1, 4):
        round_name = f"F{round_idx}"
        table_name = f"F{round_idx}A"
        for match_no in range(1, 5):
            e_sc = float(final_2021_peter[round_idx - 1][match_no - 1])
            s_sc = float(final_2021_ye[round_idx - 1][match_no - 1])
            w_sc = float(final_2021_ben[round_idx - 1][match_no - 1])
            n_sc = float(final_2021_july[round_idx - 1][match_no - 1])
            e_rk, s_rk, w_rk, n_rk = compute_ranks(e_sc, s_sc, w_sc, n_sc)
            all_rows.append(
                MatchRow(
                    year=2021,
                    phase=PHASE_FINAL,
                    round_name=round_name,
                    table_name=table_name,
                    match_no=match_no,
                    e_player_id="#028",
                    e_score=e_sc,
                    e_penalty=0.0,
                    e_rank=e_rk,
                    s_player_id="#021",
                    s_score=s_sc,
                    s_penalty=0.0,
                    s_rank=s_rk,
                    w_player_id="#067",
                    w_score=w_sc,
                    w_penalty=0.0,
                    w_rank=w_rk,
                    n_player_id="#003",
                    n_score=n_sc,
                    n_penalty=0.0,
                    n_rank=n_rk,
                )
            )

    return all_rows, pid_to_nick


def ensure_phase_column(cur) -> None:
    cur.execute(
        """
        select 1
        from information_schema.columns
        where table_schema='public' and table_name='match_result' and column_name='phase'
        """
    )
    if cur.fetchone():
        cur.execute("update match_result set phase = %s where phase is null", (PHASE_REGULAR,))
        return

    cur.execute("alter table match_result add column phase varchar(20) not null default %s", (PHASE_REGULAR,))


def upsert_player_mapping(cur, pid_to_nick: Dict[str, str]) -> None:
    for pid, nick in pid_to_nick.items():
        cur.execute(
            """
            insert into player_mapping (player_id, nickname)
            values (%s, %s)
            on conflict (player_id) do nothing
            """,
            (pid, nick),
        )


def insert_match_rows(cur, rows: List[MatchRow]) -> None:
    cur.execute(
        """
        delete from match_result
        where
          (year in (2022, 2023, 2024, 2025) and phase in (%s, %s))
          or (year = 2021 and phase = %s)
        """,
        (PHASE_SEMI, PHASE_FINAL, PHASE_FINAL),
    )

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
        [r.__dict__ for r in rows],
    )


def main() -> None:
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "postgres")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")

    rows, pid_to_nick = extract_playoffs()

    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    cur = conn.cursor()

    ensure_phase_column(cur)
    cur.execute("update match_result set phase = %s where phase is null", (PHASE_REGULAR,))

    upsert_player_mapping(cur, pid_to_nick)
    insert_match_rows(cur, rows)

    conn.commit()

    cur.execute("select year, phase, count(*) from match_result group by year, phase order by year, phase")
    print("rows_by_year_phase", cur.fetchall())

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
