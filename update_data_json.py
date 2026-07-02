import json
import re
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

import migrate


SHEET_ID = "1UzHJpjqT8GUE3rVlRcsVLb5omGYmEXZvobnm-rKCPpA"
EXPORT_XLSX_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

YEAR = 2026
PHASE_REGULAR = "Regular"
PHASE_SEMI = "Semi-Final"
PHASE_FINAL = "Final"

DATA_JSON_PATH = Path("site/public/data.json")


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
            e_rk, s_rk, w_rk, n_rk = compute_ranks(
                row["e_score"], row["s_score"], row["w_score"], row["n_score"]
            )
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


def phase_sort_value(phase: str) -> int:
    order = {
        PHASE_REGULAR: 1,
        PHASE_SEMI: 2,
        PHASE_FINAL: 3,
    }
    return order.get(str(phase), 99)


def load_existing_data_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "version": 1,
            "updated_at": None,
            "source": {},
            "years": [],
            "players": [],
            "matches": [],
        }

    return json.loads(path.read_text(encoding="utf-8"))


def merge_payload(
    existing: Dict[str, Any],
    new_rows: List[Dict[str, Any]],
    id_to_name: Dict[str, str],
) -> Dict[str, Any]:
    old_matches = existing.get("matches", [])
    kept_matches: List[Dict[str, Any]] = []

    for row in old_matches:
        try:
            row_year = int(row.get("year", 0))
        except Exception:
            row_year = 0
        if row_year != YEAR:
            kept_matches.append(row)

    merged_matches = kept_matches + new_rows
    merged_matches.sort(
        key=lambda r: (
            int(r.get("year", 0)),
            phase_sort_value(str(r.get("phase", ""))),
            str(r.get("round_name", "")),
            str(r.get("table_name", "")),
            int(r.get("match_no", 0)),
        )
    )

    players_by_id: Dict[str, Dict[str, str]] = {}

    for p in existing.get("players", []):
        pid_raw = p.get("player_id") or p.get("id") or ""
        pid = migrate.normalize_player_id(pid_raw) if pid_raw else ""
        name = str(p.get("name") or p.get("nickname") or "").strip()
        if pid and name:
            players_by_id[pid] = {"player_id": pid, "name": name}

    for pid, name in id_to_name.items():
        pid_norm = migrate.normalize_player_id(pid)
        players_by_id[pid_norm] = {
            "player_id": pid_norm,
            "name": str(name).strip(),
        }

    years = sorted(
        {
            int(row["year"])
            for row in merged_matches
            if row.get("year") is not None
        }
    )

    payload = dict(existing)
    payload["version"] = 1
    payload["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload["source"] = {
        "type": "google_sheet_xlsx_export",
        "sheet_id": SHEET_ID,
        "year": YEAR,
    }
    payload["years"] = years
    payload["players"] = sorted(players_by_id.values(), key=lambda p: p["player_id"])
    payload["matches"] = merged_matches
    return payload


def write_data_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("data_json_written", str(path))


def main() -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_dir = Path("downloads") / str(YEAR)
    xlsx_path = out_dir / f"phoenix_{YEAR}_{now}.xlsx"

    download_xlsx(xlsx_path)
    rows, id_to_name = extract_2026_from_xlsx(xlsx_path)

    existing = load_existing_data_json(DATA_JSON_PATH)
    payload = merge_payload(existing, rows, id_to_name)
    write_data_json(DATA_JSON_PATH, payload)

    phase_counts: Dict[str, int] = {}
    for r in rows:
        phase = str(r.get("phase", ""))
        phase_counts[phase] = phase_counts.get(phase, 0) + 1

    print("rows_2026_by_phase", phase_counts)


if __name__ == "__main__":
    main()