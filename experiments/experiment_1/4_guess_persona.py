#!/usr/bin/env python3
"""
Guess MBTI persona from de-identified chat files.

For each speaker in each file, asks GPT to predict the top 3 MBTI types
with probability and reasoning. Results saved to guess_results.csv.

Usage:
    python experiments/experiment_1/guess_persona.py
"""
import os
import sys
import csv
import json
import time

EXP_DIR      = os.path.dirname(__file__)
DEIDENT_DIR  = os.path.join(EXP_DIR, "data_collected_deidentified")
OUTPUT_CSV   = os.path.join(EXP_DIR, "guess_results.csv")
ROOT         = os.path.abspath(os.path.join(EXP_DIR, "../.."))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from openai import OpenAI
from data import MBTI_PERSONAS

client = OpenAI()

# ── MBTI descriptions for the prompt ─────────────────────────────────
MBTI_DESC_BLOCK = "\n".join(
    f"- {k}: {v}" for k, v in MBTI_PERSONAS.items()
)


def extract_speakers(filepath: str) -> dict[str, list[str]]:
    """Return {speaker_id: [message, message, ...]} from a de-identified file."""
    speakers = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and "]" in line:
                end = line.index("]")
                spk  = line[1:end]
                text = line[end + 2:].strip()
                if spk not in speakers:
                    speakers[spk] = []
                speakers[spk].append(text)
    return speakers


def guess_speaker(speaker_id: str, messages: list[str], full_convo: str) -> list[dict]:
    """
    Ask GPT to guess top 3 MBTI types for this speaker.
    Returns list of {type, probability, reasoning} dicts.
    """
    speaker_block = "\n".join(f"  [{speaker_id}] {m}" for m in messages)

    prompt = f"""You are an expert in MBTI personality psychology.

Below are the 16 MBTI types and their descriptions:
{MBTI_DESC_BLOCK}

Here is a full conversation between two anonymous speakers:
--- FULL CONVERSATION ---
{full_convo}
--- END ---

Focus on Speaker [{speaker_id}]'s messages:
{speaker_block}

Based on their language, tone, reasoning style, and emotional expression, predict the top 3 most likely MBTI types for Speaker [{speaker_id}].

Respond ONLY with a JSON array of exactly 3 objects, like this:
[
  {{"type": "INTJ", "probability": 0.55, "reasoning": "...one sentence..."}},
  {{"type": "ENTJ", "probability": 0.30, "reasoning": "...one sentence..."}},
  {{"type": "INTP", "probability": 0.15, "reasoning": "...one sentence..."}}
]

Rules:
- probabilities must sum to 1.0
- reasoning must be one concise sentence
- return only the JSON array, no other text"""

    for attempt in range(5):
        try:
            r = client.chat.completions.create(
                model="gpt-5.4-mini",
                max_completion_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = r.choices[0].message.content.strip()
            # strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            guesses = json.loads(raw.strip())
            return guesses
        except Exception as e:
            if "rate" in str(e).lower():
                wait = 2 ** attempt
                print(f"    [rate limit] retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"    [error] {e}")
                return []
    return []


def load_full_convo(filepath: str) -> str:
    """Read the conversation section (skip header lines)."""
    lines = []
    in_convo = False
    with open(filepath) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("[") and "]" in stripped:
                in_convo = True
            if in_convo:
                lines.append(stripped)
    return "\n".join(lines)


def main():
    chat_files = sorted(
        f for f in os.listdir(DEIDENT_DIR)
        if f.endswith(".txt") and not f.startswith(".")
    )

    if not chat_files:
        print("No de-identified files found.")
        sys.exit(0)

    rows = []

    for fname in chat_files:
        fpath     = os.path.join(DEIDENT_DIR, fname)
        speakers  = extract_speakers(fpath)
        full_conv = load_full_convo(fpath)

        print(f"\n{fname}")

        for spk_id, messages in speakers.items():
            print(f"  Guessing [{spk_id}]...", end=" ", flush=True)
            guesses = guess_speaker(spk_id, messages, full_conv)

            if not guesses:
                print("failed")
                continue

            for rank, g in enumerate(guesses[:3], 1):
                rows.append({
                    "file":        fname,
                    "speaker":     spk_id,
                    "rank":        rank,
                    "mbti_type":   g.get("type", ""),
                    "probability": g.get("probability", ""),
                    "reasoning":   g.get("reasoning", ""),
                })

            top = guesses[0]
            print(f"→ {top['type']} ({top['probability']:.0%}), "
                  f"{guesses[1]['type']} ({guesses[1]['probability']:.0%}), "
                  f"{guesses[2]['type']} ({guesses[2]['probability']:.0%})")

    # write CSV
    fieldnames = ["file", "speaker", "rank", "mbti_type", "probability", "reasoning"]
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone. {len(rows)} guesses written to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
