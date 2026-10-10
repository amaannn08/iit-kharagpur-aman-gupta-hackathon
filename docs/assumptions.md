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
| PS resources not used: Salad Money (UK trusted research environment only), News API (API key required; free plan delays articles 24 h), Alpha Vantage (yfinance covers every price series) | `scripts/data/fetch_real.py` | Live feeds come from GDELT GKG and SEC EDGAR 8-K, which need no key and are real-time |
| FRED / ICE BofA OAS rating indices used strictly for empirical calibration and validation; only derived statistics and bucket anchors stored | `sentinel.stress.calibration`, `scripts/data/calibrate_shocks.py` | Open Federal Reserve Economic Data (FRED) public series |
| SEC EDGAR XBRL company facts used to extract real debt, coverage, and equity figures for wholesale book construction | `scripts/data/build_wholesale_real.py` | Public domain SEC EDGAR financial disclosures |
| S&P Global Ratings Default Study (1981–2024) provides empirical baseline 1-year default rates by rating tier | `sentinel.stress.valuation` | Cited historical statistics from published S&P Global credit research |

## NLP

| Assumption | Where |
|---|---|
| Entity universe = S&P 500 + 16 fictional demo issuers; rating agencies, exchanges, brokers and fund sponsors are not linked as the subject when acting in that role | `sentinel.nlp.entities` |
| Share-class canonicalization: GOOG -> GOOGL, FOX -> FOXA, NWS -> NWSA, BRK-A -> BRK-B; possessive forms and compound names handled | `sentinel.nlp.entities` |
| Event abstention threshold = smallest confidence giving >= 0.90 precision on a 10% dev split of the training data (currently 0.55) | `scripts/models/train_event.py`, `models/event_v2.card.json` |
| MACRO, GEOPOLITICAL and PRODUCT labels require visible evidence in the text (evidence gates) | `sentinel.nlp.events.GATES` |
| For a credit/rates book, policy easing and falling bad-when-up indicators are positive; tightening and rising ones negative; MACRO sentiment is blended 50/50 toward that direction | `sentinel.nlp.sentiment.apply_macro_polarity` |
| Impact label = \|r - beta_120d * r_SPY\| / sigma_30d on the reaction day (same day if published before 16:00 New York, else next trading day); reaction headlines excluded | `scripts/models/train_impact.py` |
| Impact 1-10 = decile of the out-of-fold prediction; only signals with a classified event use the model, others keep the rubric; systemic signals use the rubric, capped at 7 without explicit magnitude; catastrophic language on a stress class sets a floor of 8 | `sentinel.nlp.severity` |
| Social posts are actionable only with a cashtag or financial/macro context and no spam markers | `sentinel.nlp.relevance` |
| Near-duplicates: Jaccard >= 0.75 or containment >= 0.85 (>= 4 shared tokens) within 24 hours of record time | `sentinel.replay.dedup` |

## Module B (Wholesale & Retail Stress Testing)

| Assumption | Value / Rule | Where |
|---|---|---|
| **Wholesale book construction** | 22 real debt issuers across 11 GICS sectors (2 largest per sector from S&P 100 debt filers via SEC XBRL `companyfacts`). Synthetic credit ratings derived via Damodaran coverage tables ($EBIT / \text{Interest}$) for non-financials, equity/assets for financials. Baseline 1-year PDs from S&P Global Ratings Default Study (AAA 0.00%, AA 0.02%, A 0.05%, BBB 0.15%, BB 0.60%, B 3.00%, CCC 26.0%). LGD = 45% (Basel F-IRB senior unsecured). Sizing: $EAD_i \propto \sqrt{\text{TotalDebt}_i}$, capped at 8% per single-name. 60% term loans / 40% senior unsecured bonds alternating. | `scripts/data/build_wholesale_real.py`, `data/portfolio/wholesale_real.json` |
| **Bond spread valuation** | $\Delta P \approx -D_{spread} \cdot \Delta s \cdot P$ where spread widening ($\Delta s > 0$) lowers market value. Modified duration: $D = \frac{1 - (1+y)^{-T}}{y}$ with yield $y = y_{treasury} + s_{OAS}$. Parallel spread shift assumption ($D_{spread} = D_{modified}$). | `sentinel.stress.valuation` |
| **Loan credit triangle & PD mapping** | $\Delta ECL = EAD \cdot (1 - R) \cdot \Delta PD$ with $\Delta PD = \frac{\Delta s}{1 - R}$, yielding $\Delta ECL = EAD \cdot \Delta s$. Evaluated per loan using loan-specific LGD and rating-tiered spread shock. | `sentinel.stress.valuation` |
| **Risk-neutral vs physical PD note** | Spread shock represents risk-neutral default intensity shift ($\Delta \lambda \approx \Delta s / (1 - R)$). Historical physical PDs anchor baseline ECL; stressed ECL incorporates the market-implied spread distress to capture balance-sheet credit migration under regulatory stress testing guidelines. | `sentinel.stress.valuation` |
| **No provision release** | In market-easing or positive sentiment rallies ($\Delta s < 0$), incremental loan credit loss is floored at 0 ($\Delta ECL \le 0 \implies \Delta ECL = 0$). Regulatory provisions cannot be released into P&L from temporary sentiment rallies (conservatism principle under CECL/IFRS 9). Bonds recognize full mark-to-market appreciation. | `sentinel.stress.valuation` |
| **Rating multipliers & anchors** | Baseline spreads anchored to FRED ICE BofA rating OAS buckets (AAA: 45 bp, AA: 55 bp, A: 85 bp, BBB: 125 bp, BB: 230 bp, B: 380 bp, CCC: 950 bp). Credit shocks scale proportionally across rating tiers (BB 1.5x, B 2.2x, CCC 3.5x relative to investment-grade BBB anchor). | `sentinel.stress.calibration`, `sentinel.stress.valuation` |
| **M&A shocks** | Applied strictly to the acquirer entity (reflecting post-merger debt issuance and execution friction). Scaled by consideration structure: $\times 1.5$ for debt-financed acquisitions, $\times 0.5$ for all-stock transactions. Targets do not take unsolicited credit deterioration shocks. | `sentinel.stress.shocks` |
| **Sector normalization** | All portfolio assets and shock targets normalize strictly to the 11 standard GICS sectors (`Communication Services`, `Consumer Discretionary`, `Consumer Staples`, `Energy`, `Financials`, `Health Care`, `Industrials`, `Information Technology`, `Materials`, `Real Estate`, `Utilities`) plus Non-Corporate (`Rates`, `Government / Cash`). Aliases resolve deterministically via `sentinel.stress.sectors.normalize_sector`. Scope matching uses strict equality. | `sentinel.stress.sectors`, `sentinel.stress.valuation` |
| **Contagion method** | 2-hop propagation over `data/graph_edges.csv` (10-K customer-supplier linkages + equity residual correlation graph). Shock transmission attenuation factor $\times 0.6$ per hop. Triggers on single-name CREDIT and SUPPLY_CHAIN events. | `sentinel.stress.contagion` |
| **Retail/SME sleeve** | EAD = total debt + 30% CCF on credit-card limits; PD by FICO score bucket; LGD = 80% unsecured; scaled to $50M portfolio. Sector mapped to borrower's largest MCC spend category. | `scripts/data/build_credit_sleeve.py` |
| **Equity sleeve** | 15 S&P 100 constituents ($4M each, $60M total); beta and vol estimated from 252 days of real historical returns. | `scripts/data/build_equity_sleeve.py` |
| **CYBER operational loss** | 10x observed card-fraud rate of the victim's GICS sector, applied to retail tranches within that sector. | `sentinel.stress.valuation` |
| **Interest rate swaps & cash** | Swaps valued via signed $DV01 \times \Delta y$; cash balance unchanged under stress. | `sentinel.stress.valuation` |

## Module A (Index Rebalancer)

| Assumption | Value | Where |
|---|---|---|
| **Universe** | 20 S&P 100 names with the best tweet coverage, equal base weights (5% each) | `sentinel.rebalance.engine` |
| **Sentiment EMA** | Alpha = 0.3 per signal, half-life 5 trading days | `sentinel.rebalance.engine` |
| **No-trade band** | 25 bps (0.0025); trades skipped if \|target_weight - current_weight\| < band | `sentinel.rebalance.engine` |
| **Weight constraints** | Long-only, single-name cap $\le 20\%$, GICS sector cap $\le 40\%$ | `sentinel.rebalance.engine` |
| **Transaction costs & break-even** | Turnover evaluated at 0 bps, 5 bps, and 10 bps linear execution costs. Break-even cost = active annual return / annual turnover. Stationary block bootstrap (20-day blocks, 2,000 resamples) gives 95% confidence intervals. | `sentinel.rebalance.engine`, `scripts/backtest_module_a.py` |

## Runtime & Compliance

- **Zero External Network Calls**: The backend makes strictly zero network requests during runtime. Validated on every commit by `scripts/verify_hygiene.py`.
- **Local Recording**: Real-time ingest runs out-of-process via `scripts/live/record_live.py`, appending to local files parsed by the engine.
- **Human Benchmark Independence**: Human news holdout labels (`data/eval/holdout_v2_news.csv`) were authored manually by the candidate without model pre-filling or algorithmic anchoring.
