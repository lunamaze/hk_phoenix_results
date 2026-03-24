import re

import pandas as pd


def normalize_player_id(player_id):
    """
    Normalize player ID to 3-digit format with leading zeros.
    E.g., #44 -> #044, #214 -> #214
    """
    if not isinstance(player_id, str):
        player_id = str(player_id)

    id_num = player_id.lstrip("#").strip()
    id_num = id_num.zfill(3)
    return f"#{id_num}"


def compute_ranks(e_score, s_score, w_score, n_score):
    scores = [
        float(e_score or 0),
        float(s_score or 0),
        float(w_score or 0),
        float(n_score or 0),
    ]
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


def load_player_mapping(xl, existing_mapping=None):
    """
    Extract Name -> MJBS-ID mapping from 'Seating-16' sheet.
    Update existing_mapping dict (Name -> ID).
    """
    if existing_mapping is None:
        existing_mapping = {}

    if "Seating-16" not in xl.sheet_names:
        print("Sheet 'Seating-16' not found.")
        return existing_mapping

    df = pd.read_excel(xl, sheet_name="Seating-16", header=None)

    for _, row in df.iloc[3:].iterrows():
        try:
            mjbs_id = row[22]
            name = row[23]

            if pd.notna(name) and pd.notna(mjbs_id):
                name = str(name).strip()
                mjbs_id = str(mjbs_id).strip()

                if mjbs_id.startswith("#"):
                    mjbs_id = normalize_player_id(mjbs_id)
                    existing_mapping[name] = mjbs_id
        except IndexError:
            continue

    print("Updated mapping with players from this file.")
    return existing_mapping


def process_round_sheet(xl, sheet_name, player_mapping, data_list, year):
    """
    Process a '第x輪' sheet and append data to data_list.
    """
    print(f"Processing {sheet_name} ({year})...")
    df = pd.read_excel(xl, sheet_name=sheet_name, header=None)

    round_match = re.search(r"第(\d+)輪", sheet_name)
    round_num = round_match.group(1) if round_match else sheet_name

    for row_idx in range(len(df)):
        pos_val = str(df.iloc[row_idx, 0]).strip()
        if pos_val != "E":
            continue

        try:
            if str(df.iloc[row_idx + 1, 0]).strip() != "S":
                continue
            if str(df.iloc[row_idx + 2, 0]).strip() != "W":
                continue
            if str(df.iloc[row_idx + 3, 0]).strip() != "N":
                continue
        except IndexError:
            continue

        table_name = "Unknown"
        header_row_idx = row_idx - 2

        if header_row_idx >= 0:
            header_row = df.iloc[header_row_idx]
            for col in range(len(header_row)):
                val = str(header_row[col])
                if "Table" in val:
                    match = re.search(r"Table\s*(\w+)", val)
                    if match:
                        table_name = match.group(1)
                        break
                    if col + 1 < len(header_row):
                        next_val = str(header_row[col + 1]).strip()
                        if next_val and next_val.lower() != "nan":
                            table_name = next_val
                            break

        if table_name == "Unknown":
            idx = (row_idx - 3) // 6
            suffixes = ["A", "B", "C", "D", "E", "F"]
            if 0 <= idx < len(suffixes):
                table_name = f"{round_num}{suffixes[idx]}"

        match_count = 0

        for col_start in range(1, 17, 4):
            if col_start + 3 >= len(df.columns):
                break

            name_e = df.iloc[row_idx, col_start]
            if pd.isna(name_e):
                continue

            match_count += 1
            match_no = match_count

            try:
                def get_id(name):
                    name = str(name).strip()
                    pid = player_mapping.get(name, name)
                    return normalize_player_id(pid)

                p1_name = str(df.iloc[row_idx, col_start]).strip()
                p1_score = df.iloc[row_idx, col_start + 3]
                p1_penalty = df.iloc[row_idx, col_start + 2]
                p1_id = get_id(p1_name)

                p2_name = str(df.iloc[row_idx + 1, col_start]).strip()
                p2_score = df.iloc[row_idx + 1, col_start + 3]
                p2_penalty = df.iloc[row_idx + 1, col_start + 2]
                p2_id = get_id(p2_name)

                p3_name = str(df.iloc[row_idx + 2, col_start]).strip()
                p3_score = df.iloc[row_idx + 2, col_start + 3]
                p3_penalty = df.iloc[row_idx + 2, col_start + 2]
                p3_id = get_id(p3_name)

                p4_name = str(df.iloc[row_idx + 3, col_start]).strip()
                p4_score = df.iloc[row_idx + 3, col_start + 3]
                p4_penalty = df.iloc[row_idx + 3, col_start + 2]
                p4_id = get_id(p4_name)

                def clean_score(s):
                    try:
                        val = float(s)
                        return val if not pd.isna(val) else 0.0
                    except Exception:
                        return 0.0

                entry = {
                    "year": year,
                    "phase": "Regular",
                    "round_name": f"Round {round_num}",
                    "table_name": table_name,
                    "match_no": match_no,
                    "e_player_id": p1_id,
                    "e_score": clean_score(p1_score),
                    "e_penalty": clean_score(p1_penalty),
                    "s_player_id": p2_id,
                    "s_score": clean_score(p2_score),
                    "s_penalty": clean_score(p2_penalty),
                    "w_player_id": p3_id,
                    "w_score": clean_score(p3_score),
                    "w_penalty": clean_score(p3_penalty),
                    "n_player_id": p4_id,
                    "n_score": clean_score(p4_score),
                    "n_penalty": clean_score(p4_penalty),
                }

                entry["e_rank"], entry["s_rank"], entry["w_rank"], entry["n_rank"] = compute_ranks(
                    entry["e_score"],
                    entry["s_score"],
                    entry["w_score"],
                    entry["n_score"],
                )

                data_list.append(entry)
            except IndexError:
                continue