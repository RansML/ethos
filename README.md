# Ethos — MBTI Persona Chat

An AI-powered chat simulator where MBTI personality types come to life. Chat against an AI persona, or watch two AI personas battle it out automatically.

---

## Features

- **16 MBTI personas** — each with its own tone, speech style, and emotional register
- **Human vs AI** — you pick a persona and chat against an AI playing the opposite type
- **AI vs AI (auto-battle)** — two AI personas chat with each other automatically with a readable delay
- **Browser GUI** — clean dark-mode web interface served locally via Flask
- **CLI** — terminal-based version with the same battle modes
- **Full logging** — every conversation saved as a timestamped text file in `chats/`
- **50-message cap** — conversations end automatically after 50 turns
- **Experiments** — batch runner for large-scale 16×16 persona battles with Excel tracking and persona-guessing analysis

---

## Setup

```bash
git clone https://github.com/RansML/ethos.git
cd ethos
pip install openai flask python-dotenv openpyxl python-pptx
```

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
```

---

## Usage

### Browser GUI
```bash
python main.py -gui
```
Opens at `http://localhost:5050`. Pick two personas, hit Start.

### CLI
```bash
python main.py              # with delay between auto turns
python main.py -no-delay    # no delay (faster)
```

---

## Chat Modes

| Mode | How it works |
|------|-------------|
| Human vs AI | You type, the AI responds in character |
| AI vs AI | Both personas chat automatically, 1.8s delay between turns |

Both modes support all 16 MBTI types. Either persona can also be set to **Human**.

---

## MBTI Personas

| Type | Name |
|------|------|
| INTJ | The Architect |
| INTP | The Thinker |
| ENTJ | The Commander |
| ENTP | The Debater |
| INFJ | The Advocate |
| INFP | The Mediator |
| ENFJ | The Protagonist |
| ENFP | The Campaigner |
| ISTJ | The Logistician |
| ISFJ | The Defender |
| ESTJ | The Executive |
| ESFJ | The Consul |
| ISTP | The Virtuoso |
| ISFP | The Adventurer |
| ESTP | The Entrepreneur |
| ESFP | The Entertainer |

---

## Experiments

### Experiment 1 — 16×16 Battle

All 256 persona pair combinations run against a fixed scenario, 8 battles in parallel. Run the scripts in order:

```bash
python experiments/experiment_1/1_setup_exp_tracking.py      # create Excel tracker
python experiments/experiment_1/2_collect_data.py            # run 256 battles
python experiments/experiment_1/3_deidentify_data_collected.py  # de-identify logs
python experiments/experiment_1/4_guess_persona.py           # GPT guesses MBTI per speaker
python experiments/experiment_1/5_analyze_guessed_persona.py # merge + compute accuracy
```

#### Output files

| # | File | Description |
|---|------|-------------|
| 1 | `1_tracking_collect_data.xlsx` | Excel tracker — 256 battles, 16×16 grid, batch plan |
| 2 | `data_collected/` | Raw battle logs (one `.txt` per pair) |
| 3 | `data_collected_deidentified/` | De-identified logs + `identity_map.csv` |
| 4 | `4_results_guessed_persona_with_reasons.csv` | Per-battle accuracy: true type vs GPT top-3 guesses |
| 5 | `5_results_analyzed_guessed_persona.csv` | Raw GPT guesses (file, speaker, rank, type, probability, reasoning) |

#### Excel tracker sheets

- **Experiments** — flat list of all 256 battles with status, scenario, log file, timestamps, turns, tokens, and cost
- **Grid** — 16×16 visual status grid
- **Batch Plan** — 32 batches of 8, showing which pairs run together

---

## Project Structure

```
ethos/
├── main.py                          # entry point (CLI + -gui flag)
├── gui.py                           # Flask server
├── data.py                          # shared personas, scenarios, prompt builder
├── templates/
│   └── index.html                   # browser GUI (HTML/CSS/JS)
├── chats/                           # saved conversation logs
└── experiments/
    └── experiment_1/
        ├── 1_setup_exp_tracking.py          # create Excel tracker
        ├── 2_collect_data.py                # run 256 battles
        ├── 3_deidentify_data_collected.py   # de-identify logs
        ├── 4_guess_persona.py               # GPT guesses MBTI per speaker
        ├── 5_analyze_guessed_persona.py     # merge results + accuracy
        ├── 1_tracking_collect_data.xlsx     # Excel tracker
        ├── config.md                        # experiment config + run results
        ├── data_collected/                  # raw battle logs
        └── data_collected_deidentified/     # de-identified logs + identity map
```

---

## Tech Stack

- **OpenAI gpt-5.4-mini** — powers all persona responses
- **Flask** — local web server for the GUI
- **python-dotenv** — loads API key from `.env`
- **openpyxl** — Excel tracking for experiments
- **Vanilla JS** — no frontend framework
