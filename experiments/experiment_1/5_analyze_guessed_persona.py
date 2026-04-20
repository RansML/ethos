#!/usr/bin/env python3
"""
Merge identity_map.csv + guess_results.csv into results_guessed_persona_with_reasons.csv.

For each battle file and each speaker, shows the top-3 GPT guesses alongside
the true MBTI type, and flags top-1 / top-3 correctness.

Usage:
    python experiments/experiment_1/analyze.py
"""
import os
import csv

EXP_DIR       = os.path.dirname(__file__)
DEIDENT_DIR   = os.path.join(EXP_DIR, "data_collected_deidentified")
IDENTITY_CSV  = os.path.join(DEIDENT_DIR, "identity_map.csv")
GUESS_CSV     = os.path.join(EXP_DIR, "guess_results.csv")
OUTPUT_CSV    = os.path.join(EXP_DIR, "results_guessed_persona_with_reasons.csv")


def true_type(original: str) -> str:
    """Strip -1/-2 suffix from self-match labels (e.g. 'INTJ-1' → 'INTJ')."""
    return original[:-2] if original.endswith(("-1", "-2")) else original


def load_guesses(path: str) -> dict[tuple[str, str], list[dict]]:
    """Return {(file, speaker): [rank1, rank2, rank3]} from guess_results.csv."""
    guesses: dict[tuple[str, str], list[dict]] = {}
    if not os.path.exists(path):
        return guesses
    with open(path) as f:
        for row in csv.DictReader(f):
            key = (row["file"], row["speaker"])
            guesses.setdefault(key, []).append(row)
    # sort each list by rank
    for key in guesses:
        guesses[key].sort(key=lambda r: int(r["rank"]))
    return guesses


def speaker_columns(prefix: str, persona_id: str, true_mbti: str,
                    guesses: dict) -> dict:
    """Build flat columns for one speaker."""
    rows = guesses.get((None, persona_id), [])  # filled in caller
    out = {}
    for i in range(1, 4):
        g = rows[i - 1] if i <= len(rows) else {}
        out[f"{prefix}_guess{i}"]     = g.get("mbti_type", "")
        out[f"{prefix}_prob{i}"]      = g.get("probability", "")
        out[f"{prefix}_reasoning{i}"] = g.get("reasoning", "")

    guessed_types = [r.get("mbti_type", "") for r in rows]
    out[f"{prefix}_true"]         = true_mbti
    out[f"{prefix}_top1_correct"] = int(bool(guessed_types) and guessed_types[0] == true_mbti)
    out[f"{prefix}_top3_correct"] = int(true_mbti in guessed_types)
    return out


def main():
    if not os.path.exists(IDENTITY_CSV):
        print(f"identity_map.csv not found: {IDENTITY_CSV}")
        return
    if not os.path.exists(GUESS_CSV):
        print(f"guess_results.csv not found: {GUESS_CSV}")
        return

    guesses = load_guesses(GUESS_CSV)

    rows_out = []
    with open(IDENTITY_CSV) as f:
        for row in csv.DictReader(f):
            dfile = row["deidentified_file"]
            p1_id = row["persona1_id"]
            p2_id = row["persona2_id"]
            p1_true = true_type(row["persona1_original"])
            p2_true = true_type(row["persona2_original"])

            # remap guesses dict key to include the filename
            p1_rows = guesses.get((dfile, p1_id), [])
            p2_rows = guesses.get((dfile, p2_id), [])

            def cols(prefix, speaker_id, true_mbti, speaker_rows):
                out = {}
                for i in range(1, 4):
                    g = speaker_rows[i - 1] if i <= len(speaker_rows) else {}
                    out[f"{prefix}_guess{i}"]     = g.get("mbti_type", "")
                    out[f"{prefix}_prob{i}"]      = g.get("probability", "")
                    out[f"{prefix}_reasoning{i}"] = g.get("reasoning", "")
                guessed = [r.get("mbti_type", "") for r in speaker_rows]
                out[f"{prefix}_true"]         = true_mbti
                out[f"{prefix}_top1_correct"] = int(bool(guessed) and guessed[0] == true_mbti)
                out[f"{prefix}_top3_correct"] = int(true_mbti in guessed)
                return out

            merged = {
                "original_file":      row["original_file"],
                "deidentified_file":  dfile,
                "persona1_original":  row["persona1_original"],
                "persona1_id":        p1_id,
                **cols("p1", p1_id, p1_true, p1_rows),
                "persona2_original":  row["persona2_original"],
                "persona2_id":        p2_id,
                **cols("p2", p2_id, p2_true, p2_rows),
            }
            rows_out.append(merged)

    if not rows_out:
        print("No rows to write.")
        return

    fieldnames = list(rows_out[0].keys())
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    # ── accuracy summary ──────────────────────────────────────────────
    total = len(rows_out) * 2  # two speakers per file
    p1_top1 = sum(r["p1_top1_correct"] for r in rows_out)
    p1_top3 = sum(r["p1_top3_correct"] for r in rows_out)
    p2_top1 = sum(r["p2_top1_correct"] for r in rows_out)
    p2_top3 = sum(r["p2_top3_correct"] for r in rows_out)
    all_top1 = p1_top1 + p2_top1
    all_top3 = p1_top3 + p2_top3

    n = len(rows_out)
    print(f"\nAnalysis saved to {OUTPUT_CSV}")
    print(f"\n{'─'*40}")
    print(f"  Files analysed : {n}")
    print(f"  Speakers total : {total}")
    print(f"  Top-1 accuracy : {all_top1}/{total}  ({all_top1/total:.0%})")
    print(f"  Top-3 accuracy : {all_top3}/{total}  ({all_top3/total:.0%})")
    print(f"{'─'*40}\n")


if __name__ == "__main__":
    main()
