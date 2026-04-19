#!/usr/bin/env python3
import os
import sys
import time
import random
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from data import MBTI_PERSONAS, SCENARIO_SEEDS, build_system_prompt

load_dotenv()

MAX_TURNS = 50
PERSONA_LIST = ["Human"] + list(MBTI_PERSONAS.keys())


def pick_persona(label: str) -> str:
    types = list(MBTI_PERSONAS.keys())
    print(f"\n  0. Human — you type")
    for i, key in enumerate(types, 1):
        print(f"  {i:2}. {key} — {MBTI_PERSONAS[key].split('.')[0].strip()}")
    print()
    while True:
        try:
            raw = input(f"Pick {label} (number, type, or 'human'): ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            sys.exit(0)
        if raw in ("0", "HUMAN"):
            return "Human"
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(types):
                return types[idx]
        elif raw in MBTI_PERSONAS:
            return raw
        print("  Invalid, try again.")


def ai_reply(client: OpenAI, system_prompt: str, history: list, max_tokens: int = 512) -> str:
    response = client.chat.completions.create(
        model="gpt-5.4-mini",
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system_prompt}] + history,
    )
    return response.choices[0].message.content.strip()


def build_messages_for(perspective: str, history: list) -> list:
    """Flip history so the active speaker sees themselves as 'assistant'."""
    msgs = []
    for entry in history:
        role = "assistant" if entry["speaker"] == perspective else "user"
        msgs.append({"role": role, "content": entry["content"]})
    return msgs


def open_log(p1: str, p2: str, scenario: str) -> tuple:
    chats_dir = os.path.join(os.path.dirname(__file__), "chats")
    os.makedirs(chats_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(chats_dir, f"chat_{p1}_vs_{p2}_{ts}.txt")
    f = open(path, "w")
    f.write(f"MBTI Chat — {p1} vs {p2}\n")
    f.write(f"Scenario: {scenario}\n")
    f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 60 + "\n\n")
    return f, path


def record(f, speaker: str, message: str):
    f.write(f"[{speaker}] {message}\n")
    f.flush()


def chat(p1: str, p2: str, delay: bool = True):
    client = OpenAI()
    scenario = random.choice(SCENARIO_SEEDS)

    sys1 = build_system_prompt(p1, MBTI_PERSONAS[p1], scenario) + \
        f"\n\nYou are talking with {p2 if p2 != 'Human' else 'a person'}. Keep it short and casual." \
        if p1 != "Human" else ""
    sys2 = build_system_prompt(p2, MBTI_PERSONAS[p2], scenario) + \
        f"\n\nYou are talking with {p1 if p1 != 'Human' else 'a person'}. Keep it short and casual." \
        if p2 != "Human" else ""

    log_f, log_path = open_log(p1, p2, scenario)
    history = []  # [{"speaker": "1"|"2", "content": "..."}]

    mode = "auto" if p1 != "Human" and p2 != "Human" else ("human1" if p1 == "Human" else "human2")

    print(f"\n{'='*58}")
    print(f"  Persona 1 : {p1}")
    print(f"  Persona 2 : {p2}")
    print(f"  Scenario  : {scenario}")
    print(f"  Mode      : {'AI vs AI (auto)' if mode == 'auto' else 'Human vs AI'}")
    print(f"  Log       : {log_path}")
    print(f"{'='*58}\n")

    if mode == "auto":
        print("Press Ctrl+C to stop.\n")
    else:
        print("Type your message and press Enter. Type 'quit' to stop.\n")

    # opening line from whichever AI goes first
    first_speaker = "1" if mode in ("auto", "human2") else "2"
    first_sys = sys1 if first_speaker == "1" else sys2
    first_name = p1 if first_speaker == "1" else p2

    seed_msgs = [{"role": "user", "content":
        "Open the conversation naturally, in character, already in this situation. One or two casual sentences."}]
    opening = ai_reply(client, first_sys, seed_msgs, max_tokens=200)
    history.append({"speaker": first_speaker, "content": opening})
    record(log_f, first_name, opening)

    side = ">>>" if first_speaker == "1" else "   <<<"
    print(f"{side} {first_name}: {opening}\n")

    try:
        while True:
            if len(history) >= MAX_TURNS:
                print(f"\n[Reached {MAX_TURNS} message limit. Chat ended.]")
                log_f.write(f"\n[Reached {MAX_TURNS} message limit.]\n")
                break

            last = history[-1]["speaker"]

            # ── auto mode: AI takes next turn ──────────────────────
            if mode == "auto":
                next_sp = "2" if last == "1" else "1"
                next_sys  = sys2 if next_sp == "2" else sys1
                next_name = p2  if next_sp == "2" else p1
                msgs = build_messages_for(next_sp, history)
                if delay:
                    time.sleep(1.8)
                reply = ai_reply(client, next_sys, msgs)
                history.append({"speaker": next_sp, "content": reply})
                record(log_f, next_name, reply)
                side = ">>>" if next_sp == "1" else "   <<<"
                print(f"{side} {next_name}: {reply}\n")

            # ── human mode: human types ────────────────────────────
            else:
                human_sp = "1" if mode == "human1" else "2"
                ai_sp    = "2" if mode == "human1" else "1"
                ai_sys   = sys2 if ai_sp == "2" else sys1
                ai_name  = p2  if ai_sp == "2" else p1

                if last != human_sp:
                    # human's turn
                    try:
                        user_input = input("You: ").strip()
                    except (KeyboardInterrupt, EOFError):
                        raise KeyboardInterrupt
                    if not user_input:
                        continue
                    if user_input.lower() in ("quit", "exit", "stop", "bye"):
                        break
                    record(log_f, "You", user_input)
                    history.append({"speaker": human_sp, "content": user_input})
                else:
                    # AI's turn
                    msgs = build_messages_for(ai_sp, history)
                    reply = ai_reply(client, ai_sys, msgs)
                    history.append({"speaker": ai_sp, "content": reply})
                    record(log_f, ai_name, reply)
                    print(f"\n{ai_name}: {reply}\n")

    except KeyboardInterrupt:
        pass

    print("\n[Chat ended]")
    log_f.write(f"\n[ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
    log_f.close()
    print(f"Saved to: {log_path}\n")


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    if "-gui" in sys.argv:
        import gui
        gui.launch()
        return

    print("\n=== MBTI Persona Chat ===")
    p1 = pick_persona("Persona 1")
    p2 = pick_persona("Persona 2")

    if p1 == "Human" and p2 == "Human":
        print("Both can't be Human. Try again.")
        sys.exit(1)

    chat(p1, p2, delay="-no-delay" not in sys.argv)


if __name__ == "__main__":
    main()
