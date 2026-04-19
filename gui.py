#!/usr/bin/env python3
import os
import random
import threading
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

from data import MBTI_PERSONAS, SCENARIO_SEEDS, build_system_prompt

load_dotenv()

app = Flask(__name__)
client = OpenAI()

MAX_TURNS = 50

session = {
    "persona1": "",
    "persona2": "",
    "system1": "",
    "system2": "",
    "history": [],   # [{"speaker": "1"|"2", "content": "..."}]
    "mode": "",      # "human1" | "human2" | "auto"
    "scenario": "",
    "log_file": None,
}


def open_log(p1: str, p2: str, scenario: str) -> str:
    chats_dir = os.path.join(os.path.dirname(__file__), "chats")
    os.makedirs(chats_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(chats_dir, f"chat_{p1}_vs_{p2}_{ts}.txt")
    if session["log_file"]:
        session["log_file"].write(f"\n[ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
        session["log_file"].close()
    f = open(path, "w")
    f.write(f"MBTI Chat — {p1} vs {p2}\n")
    f.write(f"Scenario: {scenario}\n")
    f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 60 + "\n\n")
    session["log_file"] = f
    return path


def write_log(speaker: str, message: str):
    if session["log_file"]:
        session["log_file"].write(f"[{speaker}] {message}\n")
        session["log_file"].flush()


def build_messages_for(perspective: str) -> list:
    """Build OpenAI messages list from the perspective of persona 1 or 2."""
    sys_prompt = session["system1"] if perspective == "1" else session["system2"]
    msgs = [{"role": "system", "content": sys_prompt}]
    for entry in session["history"]:
        role = "assistant" if entry["speaker"] == perspective else "user"
        msgs.append({"role": role, "content": entry["content"]})
    return msgs


def ai_reply(perspective: str, max_tokens: int = 512) -> str:
    msgs = build_messages_for(perspective)
    response = client.chat.completions.create(
        model="gpt-5.4-mini",
        max_tokens=max_tokens,
        messages=msgs,
    )
    return response.choices[0].message.content.strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/personas")
def personas():
    opts = [{"key": "Human", "desc": "You type"}]
    opts += [{"key": k, "desc": v.split("—")[0].strip()} for k, v in MBTI_PERSONAS.items()]
    return jsonify(opts)


@app.route("/start", methods=["POST"])
def start():
    p1 = request.json.get("persona1", "ENFP")
    p2 = request.json.get("persona2", "INTJ")
    scenario = random.choice(SCENARIO_SEEDS)

    session["persona1"] = p1
    session["persona2"] = p2
    session["scenario"] = scenario
    session["history"] = []

    desc1 = "a human participant" if p1 == "Human" else MBTI_PERSONAS[p1]
    desc2 = "a human participant" if p2 == "Human" else MBTI_PERSONAS[p2]

    other1 = p2 if p2 != "Human" else "another person"
    other2 = p1 if p1 != "Human" else "another person"

    if p1 != "Human":
        session["system1"] = build_system_prompt(p1, desc1, scenario) + \
            f"\n\nYou are talking directly with {other1}. Keep replies short and natural — like texting."
    if p2 != "Human":
        session["system2"] = build_system_prompt(p2, desc2, scenario) + \
            f"\n\nYou are talking directly with {other2}. Keep replies short and natural — like texting."

    if p1 == "Human" and p2 == "Human":
        mode = "human_both"
    elif p1 == "Human":
        mode = "human1"
    elif p2 == "Human":
        mode = "human2"
    else:
        mode = "auto"
    session["mode"] = mode

    log_path = open_log(p1, p2, scenario)

    # get opening line from whichever AI goes first
    opening = None
    if mode in ("auto", "human2"):
        opening_seed = "Open the conversation naturally, in character, already in this situation. One or two casual sentences."
        session["history"].append({"speaker": "user_seed", "content": opening_seed})
        msgs = [{"role": "system", "content": session["system1"]},
                {"role": "user", "content": opening_seed}]
        r = client.chat.completions.create(model="gpt-5.4-mini", max_tokens=200, messages=msgs)
        opening = r.choices[0].message.content.strip()
        session["history"] = [{"speaker": "1", "content": opening}]
        write_log(p1, opening)
    elif mode == "human1":
        opening_seed = "Open the conversation naturally, in character, already in this situation. One or two casual sentences."
        msgs = [{"role": "system", "content": session["system2"]},
                {"role": "user", "content": opening_seed}]
        r = client.chat.completions.create(model="gpt-5.4-mini", max_tokens=200, messages=msgs)
        opening = r.choices[0].message.content.strip()
        session["history"] = [{"speaker": "2", "content": opening}]
        write_log(p2, opening)

    return jsonify({
        "mode": mode,
        "persona1": p1,
        "persona2": p2,
        "scenario": scenario,
        "opening_speaker": "1" if mode in ("auto", "human2") else "2",
        "opening": opening,
        "log": os.path.basename(log_path),
    })


@app.route("/auto_turn", methods=["POST"])
def auto_turn():
    """Called by frontend to get the next AI message in auto mode."""
    if not session["history"]:
        return jsonify({"error": "no history"}), 400

    if len(session["history"]) >= MAX_TURNS:
        write_log("system", f"Reached {MAX_TURNS} message limit.")
        return jsonify({"done": True, "reason": f"Reached {MAX_TURNS} message limit."})

    last_speaker = session["history"][-1]["speaker"]
    next_speaker = "2" if last_speaker == "1" else "1"
    persona_name = session["persona2"] if next_speaker == "2" else session["persona1"]

    reply = ai_reply(next_speaker)
    session["history"].append({"speaker": next_speaker, "content": reply})
    write_log(persona_name, reply)

    done = len(session["history"]) >= MAX_TURNS
    return jsonify({"speaker": next_speaker, "persona": persona_name, "reply": reply, "done": done})


@app.route("/send", methods=["POST"])
def send():
    """Human sends a message."""
    text = request.json.get("message", "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400

    if len(session["history"]) >= MAX_TURNS:
        return jsonify({"error": "limit", "reason": f"Reached {MAX_TURNS} message limit."})

    mode = session["mode"]
    human_speaker = "1" if mode == "human1" else "2"
    ai_speaker = "2" if mode == "human1" else "1"
    ai_persona = session["persona2"] if ai_speaker == "2" else session["persona1"]

    write_log("You", text)
    session["history"].append({"speaker": human_speaker, "content": text})

    reply = ai_reply(ai_speaker)
    session["history"].append({"speaker": ai_speaker, "content": reply})
    write_log(ai_persona, reply)

    done = len(session["history"]) >= MAX_TURNS
    return jsonify({"speaker": ai_speaker, "persona": ai_persona, "reply": reply, "done": done})


@app.route("/stop", methods=["POST"])
def stop():
    if session["log_file"]:
        session["log_file"].write(f"\n[stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
        session["log_file"].flush()
    return jsonify({"ok": True})



def launch():
    import webbrowser
    import subprocess

    result = subprocess.run(["lsof", "-ti", "tcp:5050"], capture_output=True, text=True)
    for pid in result.stdout.split():
        subprocess.run(["kill", "-9", pid])

    threading.Timer(0.8, lambda: webbrowser.open("http://localhost:5050")).start()
    app.run(port=5050, debug=False)


if __name__ == "__main__":
    launch()

