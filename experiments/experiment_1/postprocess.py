#!/usr/bin/env python3
"""
Post-processing for Experiment 1 battle logs.

- De-identifies MBTI type names with random single letters (A, B, C…)
- Fixes spacing: no blank line between same speaker, blank line between different speakers
- Saves de-identified files to results_deidentified/
- Saves identity mapping to results_deidentified/identity_map.csv
"""
import os
import sys
import csv
import random
import string

# ── paths ─────────────────────────────────────────────────────────────
EXP_DIR   = os.path.dirname(__file__)
_data_dir = f"/data/{os.environ.get('USER', 'user')}/ethos/experiments/experiment_1/results"
RESULTS_DIR     = _data_dir if os.path.exists("/data") else os.path.join(EXP_DIR, "results")
DEIDENT_DIR     = os.path.join(EXP_DIR, "results_deidentified")
IDENTITY_MAP_CSV = os.path.join(DEIDENT_DIR, "identity_map.csv")

LETTERS = list(string.ascii_uppercase)   # A–Z


def assign_ids(personas: list[str], used: set[str]) -> dict[str, str]:
    """Assign unique random letters to each persona, avoiding already-used ones."""
    available = [l for l in LETTERS if l not in used]
    random.shuffle(available)
    mapping = {}
    for persona in personas:
        if persona not in mapping:
            mapping[persona] = available.pop(0)
    return mapping


def parse_messages(lines: list[str]) -> list[tuple[str, str]]:
    """
    Parse log lines into (speaker, text) tuples.
    Header lines (before first [SPEAKER] line) are returned as (None, line).
    """
    messages = []
    for line in lines:
        line = line.rstrip("\n")
        if line.startswith("[") and "]" in line:
            bracket_end = line.index("]")
            speaker = line[1:bracket_end]
            text    = line[bracket_end + 2:]   # skip "] "
            messages.append((speaker, text))
        else:
            messages.append((None, line))      # header / metadata / blank
    return messages


def reformat(messages: list[tuple[str, str]], id_map: dict[str, str]) -> str:
    """
    Rebuild the file:
    - Replace speaker names with their IDs
    - No blank line between consecutive same-speaker lines
    - One blank line between different speakers
    - Preserve header (non-speaker) lines as-is
    """
    out = []
    prev_speaker = None

    for speaker, text in messages:
        if speaker is None:
            # header / metadata line
            out.append(text)
            prev_speaker = None
            continue

        anon = id_map.get(speaker, speaker)

        if prev_speaker is not None and anon != prev_speaker:
            out.append("")          # blank line between different speakers

        out.append(f"[{anon}] {text}")
        prev_speaker = anon

    return "\n".join(out) + "\n"


def process_file(filepath: str, used_letters: set[str]) -> dict | None:
    """
    Process one battle log file.
    Returns the identity mapping row, or None if the file can't be parsed.
    """
    with open(filepath, "r") as f:
        raw_lines = f.readlines()

    messages  = parse_messages(raw_lines)
    personas  = list(dict.fromkeys(s for s, _ in messages if s is not None))

    if len(personas) < 2:
        return None

    id_map    = assign_ids(personas, used_letters)
    used_letters.update(id_map.values())

    reformatted = reformat(messages, id_map)

    out_name = os.path.basename(filepath)
    out_path = os.path.join(DEIDENT_DIR, out_name)
    with open(out_path, "w") as f:
        f.write(reformatted)

    return {
        "original_file": os.path.basename(filepath),
        "deidentified_file": out_name,
        **{f"persona{i+1}_original": p for i, p in enumerate(personas)},
        **{f"persona{i+1}_id": id_map[p] for i, p in enumerate(personas)},
    }


def main():
    if not os.path.exists(RESULTS_DIR):
        print(f"Results folder not found: {RESULTS_DIR}")
        sys.exit(1)

    log_files = sorted(
        f for f in os.listdir(RESULTS_DIR)
        if f.endswith(".txt") and not f.startswith(".")
    )

    if not log_files:
        print("No .txt files found in results folder.")
        sys.exit(0)

    os.makedirs(DEIDENT_DIR, exist_ok=True)

    used_letters: set[str] = set()
    rows = []

    for fname in log_files:
        fpath = os.path.join(RESULTS_DIR, fname)
        row = process_file(fpath, used_letters)
        if row:
            rows.append(row)
            p1, p2 = row["persona1_original"], row["persona2_original"]
            id1, id2 = row["persona1_id"], row["persona2_id"]
            print(f"  ✓  {fname}  →  {p1}={id1}, {p2}={id2}")
        else:
            print(f"  ✗  {fname}  — skipped (couldn't parse)")

    # write identity map CSV
    if rows:
        fieldnames = ["original_file", "deidentified_file",
                      "persona1_original", "persona1_id",
                      "persona2_original", "persona2_id"]
        with open(IDENTITY_MAP_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    print(f"\nDone. {len(rows)} files processed.")
    print(f"Output  : {DEIDENT_DIR}")
    print(f"ID map  : {IDENTITY_MAP_CSV}")


if __name__ == "__main__":
    main()
