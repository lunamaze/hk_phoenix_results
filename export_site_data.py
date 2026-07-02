import json
import io
import contextlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pandas as pd

import migrate
import import_results_2021_photos
import import_playoffs_2022_2025


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


def _clean_match_row(row: dict) -> dict:
    out = dict(row)
    for k in [
        "e_score",
        "e_penalty",
        "s_score",
        "s_penalty",
        "w_score",
        "w_penalty",
        "n_score",
        "n_penalty",
    ]:
        out[k] = _to_float(out.get(k))
    out["year"] = int(out["year"])
    out["match_no"] = int(out["match_no"])
    return out


def build_data():
    player_mapping_id_to_name: dict[str, str] = {}
    matches: list[dict] = []

    files_to_process = sorted(migrate.EXCEL_FILES, key=lambda x: x[0], reverse=True)

    with contextlib.redirect_stdout(io.StringIO()):
        for year, filepath in files_to_process:
            xl = pd.ExcelFile(filepath)

            is_2023_format = "Seating-16" not in xl.sheet_names and year == 2023
            is_2022_format = "Seating-16" not in xl.sheet_names and year == 2022

            current_file_mapping: dict[str, str] = {}
            if is_2023_format:
                current_file_mapping = migrate.load_2023_player_mapping(xl)
            elif is_2022_format:
                current_file_mapping = migrate.load_2021_22_player_mapping(xl)
            else:
                migrate.load_player_mapping(xl, current_file_mapping)

            for name, pid in current_file_mapping.items():
                pid_normalized = migrate.normalize_player_id(pid)
                if pid_normalized not in player_mapping_id_to_name:
                    player_mapping_id_to_name[pid_normalized] = name

            for sheet in xl.sheet_names:
                if not (sheet.startswith("第") and sheet.endswith("輪")):
                    continue
                if is_2023_format:
                    migrate.process_2023_round_sheet(xl, sheet, current_file_mapping, matches, year)
                elif is_2022_format:
                    migrate.process_2021_22_round_sheet(xl, sheet, current_file_mapping, matches, year)
                else:
                    migrate.process_round_sheet(xl, sheet, current_file_mapping, matches, year)

    photo_2021_mapping = import_results_2021_photos.get_2021_player_mapping_id_to_nickname()
    for pid, nick in photo_2021_mapping.items():
        if pid not in player_mapping_id_to_name:
            player_mapping_id_to_name[pid] = nick

    matches.extend(import_results_2021_photos.build_2021_match_rows())

    playoff_rows, playoff_pid_to_nick = import_playoffs_2022_2025.extract_playoffs()
    for pid, nick in playoff_pid_to_nick.items():
        if pid not in player_mapping_id_to_name:
            player_mapping_id_to_name[pid] = nick
    matches.extend([r.__dict__ for r in playoff_rows])

    years = sorted({int(m["year"]) for m in matches})
    cleaned_matches = [_clean_match_row(m) for m in matches]

    player_mapping_rows = [
        {"player_id": pid, "nickname": nick}
        for pid, nick in sorted(player_mapping_id_to_name.items())
        if isinstance(pid, str) and pid.startswith("#")
    ]

    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "years": years,
        "player_mapping": player_mapping_rows,
        "matches": cleaned_matches,
    }
    return data


def main():
    data = build_data()
    out_path = "site/public/data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Wrote {out_path}")
    print(f"Years: {data['years']}")
    print(f"Players: {len(data['player_mapping'])}")
    print(f"Matches: {len(data['matches'])}")


if __name__ == "__main__":
    main()
