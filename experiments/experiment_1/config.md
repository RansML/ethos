# Experiment 1 — Configuration

## Model
| Parameter | Value |
|-----------|-------|
| Provider  | OpenAI |
| Model     | `gpt-5.4-mini` |
| Max tokens per reply | 256 (opening: 150) |

## Battle Setup
| Parameter | Value |
|-----------|-------|
| Personas  | All 16 MBTI types |
| Total battles | 256 (16 × 16, including self-matches) |
| Parallel workers | 8 |
| Total batches | 32 |
| Max turns per battle | 50 (shared, both sides combined) |

## Scenario
> "a tense family dinner where something unexpected was just revealed"

Fixed for all 256 battles (`SCENARIO_SEEDS[0]`).

## Output
| Item | Location |
|------|----------|
| Battle logs | `experiments/experiment_1/data_collected/` |
| Excel tracker | `experiments/experiment_1/1_tracking_collect_data.xlsx` |

## Tracker Sheets
- **Experiments** — 256 rows: ID, Persona 1, Persona 2, Status, Scenario, Log File, Start Time, End Time, Turns
- **Grid** — 16×16 status grid (rows = Persona 1, columns = Persona 2)
- **Batch Plan** — 32 batches of 8, showing which pairs run together
