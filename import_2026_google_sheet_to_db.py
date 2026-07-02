import os
import re
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import psycopg2

import migrate


SHEET_ID = "1UzHJpjqT8GUE3rVlRcsVLb5omGYmEXZvobnm-rKCPpA"
EXPORT_XLSX_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

YEAR = 2026
PHASE_REGULAR = "Regular"
PHASE_SEMI = "Semi-Final"
PHASE_FINAL = "Final"


def compute_ranks(e: float, s: float, w: float, n: float) -> Tuple[int, int, int, int]:
    scores = [float(e), float(s), float(w), float(n)]
    ranks: List[int] = []
    for i, si in enumerate(scores):
        better = 0
        for j, sj in enumerate(scores):
            if i == j:
                continue
            if sj > si:
                better += 1
        ranks.append(1 + better)
    return ranks[0], ranks[1], ranks[2], ranks[3]


def _to_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, float):
        return v
    if isinstance(v, int):
        return float(v)
    try:
        return float(v)
    except Exception:
        return 0.0


def normalize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        row["year"] = int(row.get("year") or YEAR)
        row["phase"] = str(row.get("phase") or PHASE_REGULAR)
        row["round_name"] = str(row.get("round_name") or "")
        row["table_name"] = str(row.get("table_name") or "")
        row["match_no"] = int(row.get("match_no") or 0)

        row["e_score"] = _to_float(row.get("e_score"))
        row["s_score"] = _to_float(row.get("s_score"))
        row["w_score"] = _to_float(row.get("w_score"))
        row["n_score"] = _to_float(row.get("n_score"))
        row["e_penalty"] = _to_float(row.get("e_penalty"))
        row["s_penalty"] = _to_float(row.get("s_penalty"))
        row["w_penalty"] = _to_float(row.get("w_penalty"))
        row["n_penalty"] = _to_float(row.get("n_penalty"))

        if all(k in row for k in ["e_rank", "s_rank", "w_rank", "n_rank"]) and all(
            isinstance(row[k], (int, float)) for k in ["e_rank", "s_rank", "w_rank", "n_rank"]
        ):
            row["e_rank"] = int(row["e_rank"])
            row["s_rank"] = int(row["s_rank"])
            row["w_rank"] = int(row["w_rank"])
            row["n_rank"] = int(row["n_rank"])
        else:
            e_rk, s_rk, w_rk, n_rk = compute_ranks(row["e_score"], row["s_score"], row["w_score"], row["n_score"])
            row["e_rank"] = int(e_rk)
            row["s_rank"] = int(s_rk)
            row["w_rank"] = int(w_rk)
            row["n_rank"] = int(n_rk)

        out.append(row)
    return out


def is_empty_match_row(row: Dict[str, Any]) -> bool:
    def z(x: Any) -> bool:
        try:
            return abs(float(x)) < 1e-9
        except Exception:
            return True

    return (
        z(row.get("e_score"))
        and z(row.get("s_score"))
        and z(row.get("w_score"))
        and z(row.get("n_score"))
        and z(row.get("e_penalty"))
        and z(row.get("s_penalty"))
        and z(row.get("w_penalty"))
        and z(row.get("n_penalty"))
    )


def download_xlsx(dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        EXPORT_XLSX_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        method="GET",
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Download failed: HTTP {resp.status}")
        dest_path.write_bytes(resp.read())


def load_name_list_mapping(xl: pd.ExcelFile) -> Dict[str, str]:
    if "Name List" not in xl.sheet_names:
        return {}
    df = pd.read_excel(xl, sheet_name="Name List", header=None)

    name_col = None
    id_col = None
    for r in range(min(10, len(df))):
        for c in range(min(10, df.shape[1])):
            v = df.iat[r, c]
            if pd.isna(v):
                continue
            s = str(v).strip()
            if s.lower() == "name":
                name_col = c
            if s.upper() == "HKMA ID":
                id_col = c
        if name_col is not None and id_col is not None:
            header_row = r
            break
    else:
        return {}

    mapping: Dict[str, str] = {}
    for r in range(header_row + 1, len(df)):
        name = df.iat[r, name_col]
        hkma = df.iat[r, id_col]
        if pd.isna(name) or pd.isna(hkma):
            continue
        name_s = str(name).strip()
        hkma_s = str(hkma).strip()
        hkma_s = re.sub(r"\D", "", hkma_s)
        if not hkma_s:
            continue
        mapping[name_s] = f"#{int(hkma_s):03d}"

    return mapping


def normalize_name_key(name: Any) -> str:
    s = str(name).strip()
    s = " ".join(s.split())
    s = s.casefold()
    s = re.sub(r"[\s._-]+", "", s)
    return s


def build_name_to_id(mapping: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name, pid in mapping.items():
        out[normalize_name_key(name)] = str(pid).strip()
    return out


def parse_eswn_sheet(
    xl: pd.ExcelFile,
    sheet_name: str,
    phase: str,
    name_to_id: Dict[str, str],
) -> List[Dict[str, Any]]:
    df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    out: List[Dict[str, Any]] = []

    def resolve_id(name: Any) -> str:
        pid = name_to_id.get(normalize_name_key(name))
        if not pid:
            raise ValueError(f"[{sheet_name}] Unresolved name: {name}")
        return migrate.normalize_player_id(pid)

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

            names = [df.iat[row_idx + i, col_start] for i in range(4)]
            if any(pd.isna(n) for n in names):
                continue

            table_name = None
            for back in range(1, 4):
                if row_idx - back < 0:
                    break
                maybe = df.iat[row_idx - back, col_start + 3]
                if pd.notna(maybe) and str(maybe).strip():
                    table_name = str(maybe).strip()
                    break
            if not table_name:
                table_name = sheet_name

            penalties = [df.iat[row_idx + i, col_start + 2] for i in range(4)]
            scores = [df.iat[row_idx + i, col_start + 3] for i in range(4)]

            pids = [resolve_id(n) for n in names]
            e_pid, s_pid, w_pid, n_pid = pids
            e_pen, s_pen, w_pen, n_pen = (_to_float(x) for x in penalties)
            e_sc, s_sc, w_sc, n_sc = (_to_float(x) for x in scores)
            e_rk, s_rk, w_rk, n_rk = compute_ranks(e_sc, s_sc, w_sc, n_sc)

            match_no = int(((col_start - 1) / 4) + 1)
            out.append(
                {
                    "year": YEAR,
                    "phase": phase,
                    "round_name": sheet_name,
                    "table_name": table_name,
                    "match_no": match_no,
                    "e_player_id": e_pid,
                    "e_score": e_sc,
                    "e_penalty": e_pen,
                    "e_rank": e_rk,
                    "s_player_id": s_pid,
                    "s_score": s_sc,
                    "s_penalty": s_pen,
                    "s_rank": s_rk,
                    "w_player_id": w_pid,
                    "w_score": w_sc,
                    "w_penalty": w_pen,
                    "w_rank": w_rk,
                    "n_player_id": n_pid,
                    "n_score": n_sc,
                    "n_penalty": n_pen,
                    "n_rank": n_rk,
                }
            )

    return out


def extract_2026_from_xlsx(xlsx_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    xl = pd.ExcelFile(str(xlsx_path))

    current_file_mapping: Dict[str, str] = {}
    if "Name List" in xl.sheet_names:
        current_file_mapping = load_name_list_mapping(xl)
    elif "Seating-16" in xl.sheet_names:
        migrate.load_player_mapping(xl, current_file_mapping)
    elif "第1輪" in xl.sheet_names:
        current_file_mapping = migrate.load_2021_22_player_mapping(xl)
    else:
        current_file_mapping = migrate.load_2023_player_mapping(xl)

    player_mapping_id_to_name: Dict[str, str] = {}
    for name, pid in current_file_mapping.items():
        pid_norm = migrate.normalize_player_id(pid)
        if pid_norm not in player_mapping_id_to_name:
            player_mapping_id_to_name[pid_norm] = str(name).strip()

    matches: List[Dict[str, Any]] = []
    for sheet in xl.sheet_names:
        if not (sheet.startswith("第") and sheet.endswith("輪")):
            continue
        if "Name List" in xl.sheet_names or "Seating-16" in xl.sheet_names:
            migrate.process_round_sheet(xl, sheet, current_file_mapping, matches, YEAR)
        elif "第1輪" in xl.sheet_names:
            migrate.process_2021_22_round_sheet(xl, sheet, current_file_mapping, matches, YEAR)
        else:
            migrate.process_2023_round_sheet(xl, sheet, current_file_mapping, matches, YEAR)

    if "Name List" in xl.sheet_names:
        name_to_id = build_name_to_id(current_file_mapping)
        for s in ["SF1", "SF2", "SF3"]:
            if s in xl.sheet_names:
                matches.extend(parse_eswn_sheet(xl, s, PHASE_SEMI, name_to_id))
        for s in ["F1", "F2", "F3"]:
            if s in xl.sheet_names:
                matches.extend(parse_eswn_sheet(xl, s, PHASE_FINAL, name_to_id))

    cleaned = normalize_rows(matches)
    non_empty = [r for r in cleaned if not is_empty_match_row(r)]
    print("rows_extracted_total", len(cleaned))
    print("rows_extracted_non_empty", len(non_empty))
    return non_empty, player_mapping_id_to_name


def ensure_columns(cur) -> None:
    cur.execute("alter table match_result add column if not exists phase varchar(20) not null default %s", (PHASE_REGULAR,))
    cur.execute("alter table match_result add column if not exists e_rank integer")
    cur.execute("alter table match_result add column if not exists s_rank integer")
    cur.execute("alter table match_result add column if not exists w_rank integer")
    cur.execute("alter table match_result add column if not exists n_rank integer")


def ensure_player_mapping_columns(cur) -> None:
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


def upsert_player_mapping(cur, id_to_name: Dict[str, str]) -> None:
    for pid, name in id_to_name.items():
        cur.execute(
            """
            insert into player_mapping (player_id, nickname)
            values (%s, %s)
            on conflict (player_id) do nothing
            """,
            (pid, name),
        )


def load_canonical_player_ids_by_nickname(cur) -> Dict[str, str]:
    cur.execute(
        """
        with ids as (
          select distinct unnest(array[e_player_id, s_player_id, w_player_id, n_player_id]) as player_id
          from match_result
          where year between 2021 and 2025
        )
        select pm.player_id, pm.nickname
        from player_mapping pm
        join ids on ids.player_id = pm.player_id
        where pm.nickname is not null
        """
    )
    nick_key_to_player_id: Dict[str, str] = {}
    for pid, nick in cur.fetchall():
        nick_s = str(nick or "").strip()
        if not nick_s:
            continue
        nick_key_to_player_id[normalize_name_key(nick_s)] = str(pid)
    return nick_key_to_player_id


def upsert_player_id_new(cur, new_id_to_name: Dict[str, str]) -> Dict[str, str]:
    nick_key_to_player_id = load_canonical_player_ids_by_nickname(cur)
    new_id_to_effective_player_id: Dict[str, str] = {}
    updated_existing = 0
    created_new = 0
    deleted_dupe = 0

    for new_id, name in new_id_to_name.items():
        new_id_norm = migrate.normalize_player_id(new_id)
        name_s = str(name).strip()
        existing_pid = nick_key_to_player_id.get(normalize_name_key(name_s))

        if existing_pid:
            cur.execute(
                "update player_mapping set player_id_new = null where player_id_new = %s and player_id <> %s",
                (new_id_norm, existing_pid),
            )
            cur.execute("delete from player_mapping where player_id = %s and player_id <> %s", (new_id_norm, existing_pid))

            cur.execute(
                "update player_mapping set player_id_new = %s where player_id = %s",
                (new_id_norm, existing_pid),
            )
            new_id_to_effective_player_id[new_id_norm] = existing_pid
            updated_existing += 1

            cur.execute(
                """
                delete from player_mapping pm
                where pm.player_id = %s and pm.player_id <> %s and pm.nickname = %s
                  and not exists (
                    select 1
                    from match_result mr
                    where pm.player_id in (mr.e_player_id, mr.s_player_id, mr.w_player_id, mr.n_player_id)
                  )
                """,
                (new_id_norm, existing_pid, name_s),
            )
            deleted_dupe += cur.rowcount
            continue

        cur.execute("update player_mapping set player_id_new = null where player_id_new = %s and player_id <> %s", (new_id_norm, new_id_norm))
        cur.execute(
            """
            insert into player_mapping (player_id, nickname, player_id_new)
            values (%s, %s, %s)
            on conflict (player_id) do update set
              nickname = excluded.nickname,
              player_id_new = excluded.player_id_new
            """,
            (new_id_norm, name_s, new_id_norm),
        )
        new_id_to_effective_player_id[new_id_norm] = new_id_norm
        created_new += 1

    print("player_id_new_updated_existing", updated_existing)
    print("player_id_new_created_new", created_new)
    print("player_id_new_deleted_duplicates", deleted_dupe)

    return new_id_to_effective_player_id


def remap_match_player_ids(rows: List[Dict[str, Any]], new_to_effective: Dict[str, str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        for k in ["e_player_id", "s_player_id", "w_player_id", "n_player_id"]:
            pid = migrate.normalize_player_id(row[k])
            row[k] = new_to_effective.get(pid, pid)
        out.append(row)
    return out



def insert_rows(cur, rows: List[Dict[str, Any]]) -> None:
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
        rows,
    )


def main() -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = Path("downloads") / "2026"
    xlsx_path = out_dir / f"phoenix_2026_{now}.xlsx"

    download_xlsx(xlsx_path)
    rows, id_to_name = extract_2026_from_xlsx(xlsx_path)

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    cur = conn.cursor()
    ensure_columns(cur)
    ensure_player_mapping_columns(cur)

    cur.execute("delete from match_result where year = %s", (YEAR,))

    upsert_player_id_new(cur, id_to_name)

    if rows:
        insert_rows(cur, rows)

    conn.commit()

    cur.execute("select year, phase, count(1) from match_result where year=%s group by year, phase order by phase", (YEAR,))
    print("rows_2026_by_phase", cur.fetchall())

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
