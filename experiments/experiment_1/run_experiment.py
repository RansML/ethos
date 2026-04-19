#!/usr/bin/env python3
"""
Experiment 1 — 16 vs 16 MBTI Battle
All 256 persona pairs (16×16), run 8 at a time in parallel.
Results saved to experiments/experiment_1/chats/ and tracked in tracking.xlsx.

Usage:
    python experiments/experiment_1/run_experiment.py
"""
import os
import sys
import random
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# ── paths ─────────────────────────────────────────────────────────────
ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CHATS_DIR   = os.path.join(os.path.dirname(__file__), "results")
TRACKING_XL = os.path.join(os.path.dirname(__file__), "tracking.xlsx")
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from data import MBTI_PERSONAS, SCENARIO_SEEDS, build_system_prompt
from openai import OpenAI

TYPES       = list(MBTI_PERSONAS.keys())          # 16 types
MAX_TURNS   = 50
BATCH_SIZE  = 8
SCENARIO    = SCENARIO_SEEDS[0]                   # "a tense family dinner where something unexpected was just revealed"


# ── all 256 pairs ─────────────────────────────────────────────────────
def all_pairs() -> list[tuple[str, str]]:
    return [(p1, p2) for p1 in TYPES for p2 in TYPES]


# ── single battle ─────────────────────────────────────────────────────
def run_battle(pair: tuple[str, str]) -> dict:
    p1, p2 = pair
    os.makedirs(CHATS_DIR, exist_ok=True)

    scenario   = SCENARIO
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_name   = f"{p1}_vs_{p2}_{timestamp}.txt"
    log_path   = os.path.join(CHATS_DIR, log_name)

    sys1 = build_system_prompt(p1, MBTI_PERSONAS[p1], scenario) + \
           f"\n\nYou are talking with {p2}. Keep it short and casual."
    sys2 = build_system_prompt(p2, MBTI_PERSONAS[p2], scenario) + \
           f"\n\nYou are talking with {p1}. Keep it short and casual."

    client  = OpenAI()
    history = []   # [{"speaker": "1"|"2", "content": str}]

    def msgs_for(perspective: str) -> list:
        out = []
        for e in history:
            out.append({"role": "assistant" if e["speaker"] == perspective else "user",
                        "content": e["content"]})
        return out

    def reply(perspective: str, max_tok: int = 256) -> str:
        sys_p = sys1 if perspective == "1" else sys2
        r = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=max_tok,
            messages=[{"role": "system", "content": sys_p}] + msgs_for(perspective),
        )
        return r.choices[0].message.content.strip()

    start = datetime.now()

    with open(log_path, "w") as f:
        f.write(f"Experiment 1 — {p1} vs {p2}\n")
        f.write(f"Scenario: {scenario}\n")
        f.write(f"Started: {start.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        # opening from p1
        seed = [{"role": "user", "content":
                 "Open the conversation naturally, in character, already in this situation. One or two casual sentences."}]
        opening = client.chat.completions.create(
            model="gpt-4o", max_tokens=150,
            messages=[{"role": "system", "content": sys1}] + seed,
        ).choices[0].message.content.strip()

        history.append({"speaker": "1", "content": opening})
        f.write(f"[{p1}] {opening}\n")

        while len(history) < MAX_TURNS:
            last     = history[-1]["speaker"]
            next_sp  = "2" if last == "1" else "1"
            next_name = p2 if next_sp == "2" else p1
            text     = reply(next_sp)
            history.append({"speaker": next_sp, "content": text})
            f.write(f"[{next_name}] {text}\n")
            f.flush()

        end = datetime.now()
        f.write(f"\n[ended: {end.strftime('%Y-%m-%d %H:%M:%S')}]\n")

    return {
        "p1": p1, "p2": p2,
        "scenario": scenario,
        "turns": len(history),
        "log": log_name,
        "start": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end": end.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "done",
    }


# ── excel update ──────────────────────────────────────────────────────
def update_excel(results: list[dict]):
    from openpyxl import load_workbook
    wb = load_workbook(TRACKING_XL)

    # ── Sheet 1: flat list ─────────────────────────────────────────
    ws = wb["Experiments"]
    lookup = {(r["p1"], r["p2"]): r for r in results}

    for row in ws.iter_rows(min_row=2):
        p1_cell, p2_cell = row[1].value, row[2].value
        if (p1_cell, p2_cell) in lookup:
            r = lookup[(p1_cell, p2_cell)]
            row[3].value = r["status"]
            row[4].value = r["scenario"]
            row[5].value = r["log"]
            row[6].value = r["start"]
            row[7].value = r["end"]
            row[8].value = r["turns"]

    # ── Sheet 2: grid ─────────────────────────────────────────────
    wg = wb["Grid"]
    for r in results:
        ri = TYPES.index(r["p1"]) + 2
        ci = TYPES.index(r["p2"]) + 2
        wg.cell(row=ri, column=ci).value = r["status"]

    wb.save(TRACKING_XL)


# ── main ─────────────────────────────────────────────────────────────
def main():
    pairs = all_pairs()
    total = len(pairs)
    print(f"\nExperiment 1 — {total} battles ({BATCH_SIZE} parallel)\n")

    all_results = []
    batches     = [pairs[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    for b_idx, batch in enumerate(batches):
        print(f"Batch {b_idx+1}/{len(batches)} — running {len(batch)} battles...")
        batch_results = []

        with ProcessPoolExecutor(max_workers=BATCH_SIZE) as ex:
            futures = {ex.submit(run_battle, pair): pair for pair in batch}
            for fut in as_completed(futures):
                pair = futures[fut]
                try:
                    result = fut.result()
                    batch_results.append(result)
                    print(f"  ✓  {result['p1']} vs {result['p2']} — {result['turns']} turns")
                except Exception as e:
                    p1, p2 = pair
                    print(f"  ✗  {p1} vs {p2} — ERROR: {e}")
                    batch_results.append({
                        "p1": p1, "p2": p2, "scenario": "", "turns": 0,
                        "log": "", "start": "", "end": "", "status": f"error: {e}",
                    })

        all_results.extend(batch_results)
        update_excel(batch_results)
        print(f"  → tracking.xlsx updated\n")

    print(f"Done. {len(all_results)} battles completed.")
    print(f"Tracking: {TRACKING_XL}")
    print(f"Logs:     {CHATS_DIR}\n")


if __name__ == "__main__":
    main()
