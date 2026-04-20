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


def parse_messages(lines: list[str]) -> list[tuple[str | None, str]]:
    """
    Parse log lines into (speaker, text) tuples.
    - Header lines (before first [SPEAKER]) are (None, line).
    - Continuation lines belonging to the same speaker are merged into
      the previous message, joined with a space.
    """
    messages  = []
    in_header = True

    for line in lines:
        line = line.rstrip("\n")

        if line.startswith("[") and "]" in line:
            in_header   = False
            bracket_end = line.index("]")
            speaker     = line[1:bracket_end]
            text        = line[bracket_end + 2:].strip()
            messages.append([speaker, text])

        elif in_header:
            messages.append([None, line])

        else:
            # continuation — belongs to last speaker
            stripped = line.strip()
            if stripped and messages and messages[-1][0] is not None:
                messages[-1][1] = (messages[-1][1] + " " + stripped).strip()
            # blank continuation lines are ignored

    return [(s, t) for s, t in messages]


def reformat(messages: list[tuple[str | None, str]], id_map: dict[str, str]) -> str:
    """
    Rebuild the file:
    - Replace speaker names with their IDs
    - One blank line between different speakers
    - No blank line between consecutive messages from the same speaker
    - Preserve header lines as-is
    """
    out          = []
    prev_speaker = None

    for speaker, text in messages:
        if speaker is None:
            out.append(text)
            prev_speaker = None
            continue

        anon = id_map.get(speaker, speaker)

        if prev_speaker is not None and anon != prev_speaker:
            out.append("")          # blank line between speakers

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

    if len(personas) < 1:
        return None
    # old-format self-match: only one unique name (e.g. [INTJ] for both sides)
    # new-format self-match: INTJ-1 / INTJ-2 already distinct
    if len(personas) == 1:
        base = personas[0][:-2] if personas[0].endswith("-1") else personas[0]
        personas = [f"{base}-1", f"{base}-2"]

    id_map    = assign_ids(personas, used_letters)
    used_letters.update(id_map.values())

    reformatted = reformat(messages, id_map)

    # rename file using assigned letters instead of MBTI types
    orig_name = os.path.basename(filepath)
    # strip "P1_vs_P2_" prefix → keep "20260419_170738.txt"
    suffix    = "_".join(orig_name.split("_")[3:])
    id1, id2  = id_map[personas[0]], id_map[personas[1]]
    out_name  = f"{id1}_vs_{id2}_{suffix}"
    out_path  = os.path.join(DEIDENT_DIR, out_name)
    with open(out_path, "w") as f:
        f.write(reformatted)

    return {
        "original_file": orig_name,
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
