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
- **Experiments** — batch runner for large-scale 16×16 persona battles with Excel tracking

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
All 256 persona pair combinations run against a fixed scenario, 8 battles in parallel.

```bash
python experiments/experiment_1/run_experiment.py
```

Results land in `experiments/experiment_1/results/`. Progress is tracked in `experiments/experiment_1/tracking.xlsx` with three sheets:

- **Experiments** — flat list of all 256 battles with status, scenario, log file, timestamps, and turn count
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
├── experiments/
│   └── experiment_1/
│       ├── run_experiment.py        # 16×16 batch runner
│       ├── setup_tracking.py        # generates tracking.xlsx
│       ├── tracking.xlsx            # Excel tracker
│       └── results/                 # battle logs
└── MBTI_Chat_Presentation.pptx      # project presentation
```

---

## Tech Stack

- **OpenAI GPT-4o** — powers all persona responses
- **Flask** — local web server for the GUI
- **python-dotenv** — loads API key from `.env`
- **openpyxl** — Excel tracking for experiments
- **Vanilla JS** — no frontend framework
