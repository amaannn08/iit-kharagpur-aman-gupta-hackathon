# Assumptions and design decisions

Every assumption below is implemented in code; the file that owns it is named so it can be checked.

## Data

| Assumption | Where | Note |
|---|---|---|
| Real datasets are used as published; labels from other models (Polygon LLM sentiment, tweet TextBlob/LSTM polarity) are *silver* and never used as gold | `scripts/data/convert_real.py` | Silver labels live in separate files the engine never reads |
| Topic labels are mapped to the PS event taxonomy; credit-distress language -> CREDIT and explicit earnings language on an otherwise-OTHER topic -> EARNINGS | `sentinel.nlp.events.ps_aligned_label` | 691 of 16,990 training rows refined; evaluation reports both the plain and the aligned mapping |
| 8-K item codes are labels: 1.05 -> CYBER; 1.03, 2.04 -> CREDIT; 2.02 -> EARNINGS; 5.02, 7.01, 8.01, 2.03 -> OTHER | `scripts/data/fetch_real.py` | Routine filings that also report a distress item are excluded |
| Weak labels: real headlines matching strict supply-chain / cyber patterns | `scripts/models/train_event.py` | Excluded from the human-labeling sample |
| Tweets are dated only (`timestamp_quality = date_only`) | converters | Replay orders them by date then id |
| GDELT GKG themes are never used as labels or classifier input | `convert_real.parse_gkg_rows` | Themes are article-level and often do not match the headline |
| The 105-row author-written set is a regression check, not a benchmark | `data/eval/synthetic_regression.csv` | Same fictional issuers as the demo |

## NLP

| Assumption | Where |
|---|---|
| Entity universe = S&P 500 + 16 fictional demo issuers; rating agencies, exchanges, brokers and fund sponsors are not linked as the subject when acting in that role | `sentinel.nlp.entities` |
| Event abstention threshold = smallest confidence giving >= 0.90 precision on a 10% dev split of the training data (currently 0.55) | `scripts/models/train_event.py`, `models/event_v2.card.json` |
| MACRO, GEOPOLITICAL and PRODUCT labels require visible evidence in the text (evidence gates) | `sentinel.nlp.events.GATES` |
| For a credit/rates book, policy easing and falling bad-when-up indicators are positive; tightening and rising ones negative; MACRO sentiment is blended 50/50 toward that direction | `sentinel.nlp.sentiment.apply_macro_polarity` |
| Impact label = |r - beta_120d * r_SPY| / sigma_30d on the reaction day (same day if published before 16:00 New York, else next trading day); reaction headlines excluded | `scripts/models/train_impact.py` |
| Impact 1-10 = decile of the out-of-fold prediction; only signals with a classified event use the model, others keep the rubric; systemic signals use the rubric, capped at 7 without explicit magnitude; catastrophic language on a stress class sets a floor of 8 | `sentinel.nlp.severity` |
| Social posts are actionable only with a cashtag or financial/macro context and no spam markers | `sentinel.nlp.relevance` |
| Near-duplicates: Jaccard >= 0.75 or containment >= 0.85 (>= 4 shared tokens) within 24 hours of record time | `sentinel.replay.dedup` |

## Module B

| Assumption | Value | Where |
|---|---|---|
| Wholesale book | $500M synthetic loans/bonds/cash + $150M gross swap notional (MTM 0) | `data/wholesale_positions.json` |
| Retail/SME sleeve EAD | total debt + 30% CCF on credit-card limits | `scripts/data/build_credit_sleeve.py` |
| Retail PD by credit score | < 580: 20%, 580-640: 10%, 640-700: 4%, 700-760: 1.5%, >= 760: 0.5% | same |
| Retail LGD / size | 80% unsecured; scaled to $50M (scale factor recorded in the file) | same |
| Retail sector | GICS sector of the borrower's largest card-spend MCC category | same |
| Equity sleeve | 15 S&P 100 names, $4M each (synthetic sizes), beta/vol from 252 days of real returns | `scripts/data/build_equity_sleeve.py` |
| HY spread proxy | -(HYG return - IEF return) / 3.7 (HYG duration approximation) | `scripts/data/calibrate_shocks.py` |
| PD shock | credit triangle: dPD = d_spread / 0.6 | same |
| Systemic shocks at impact 8 | measured windows: MACRO tightening = Fed Jun-2022, easing = Fed pivot 2023, CREDIT systemic = SVB 2023, GEOPOLITICAL = Russia 2022 | `sentinel.stress.shocks` |
| Single-name shocks | CREDIT +150 bp / +2.5 pp PD / +5 pp LGD / equity -15%; SUPPLY_CHAIN +80 bp / +1.2 pp / +3 pp / -6%; CYBER +60 bp / +0.8 pp / +2 pp / -5% | same |
| Shock scaling | linear in impact / 8, bounded to [0.125, 1.25] | same |
| CYBER operational loss | 10x the observed card-fraud rate of the victim's sector, on retail tranches in that sector | `sentinel.stress.valuation` |
| Valuation | loans: incremental ECL = EAD x (PD x LGD stressed - baseline); bonds: -D x V x (dy + ds); swaps: signed DV01 x dy; equities: beta x market shock (systemic) or idiosyncratic shock (entity); cash unchanged | `sentinel.stress.valuation` |
| Contagion | 2 hops over `data/graph_edges.csv`, transmission factor x 0.6 per hop, CREDIT/SUPPLY_CHAIN entity events | `sentinel.stress.contagion` |

## Module A

| Assumption | Value | Where |
|---|---|---|
| Universe | 20 S&P 100 names with the best tweet coverage, equal base weights | `sentinel.rebalance.engine` |
| Sentiment EMA | alpha 0.3 per signal, half-life 5 days | same |
| Weights | base x (1 + 1.5 x EMA), long-only, <= 20% per name, <= 40% per sector | same |

## Runtime

- The application makes no network calls (enforced by `scripts/verify_hygiene.py`). Real-time data arrives through `scripts/live/record_live.py`, a separate process that writes local files.
- Labels on the human news holdout must be the candidate's own; the sampler never writes model predictions into the labeling file.
