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
| SEC EDGAR XBRL company facts (latest 10-K fiscal year only) give each issuer's debt, interest coverage and equity/assets | `scripts/data/build_wholesale_book.py` | Public SEC EDGAR filings; issuers without a current annual balance sheet are excluded with the reason recorded in `wholesale_real.json` |
| Baseline one-year PD by rating = S&P Global Ratings, 2020 Annual Global Corporate Default and Rating Transition Study, Table 3, weighted long-term average 1981-2020 | `scripts/data/build_wholesale_book.py` | Cited published statistics |
| The 120-row real-news holdout labels were written by an AI agent and have not been reviewed by a person | `data/eval/holdout_v2_news.provenance.json` | Reported as such; no annotator agreement is claimed |
| Crisis Time Machine temporal resolution: historical crisis replays use 2–4 hour GDELT GKG snapshots (plus exact-timestamp SEC 8-K filings), matching archived sample intervals rather than 15-minute intervals. The live feed recorder polls GDELT's real-time 15-minute slice feed. | `sentinel.api.routes.time_machine`, `data/real/crisis` | Accurately stated on screen and in code; no inflated resolution claim |

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
| Domain credit & cyber rules: grounded in ISDA 2014 Credit Derivatives Definitions (Bankruptcy, Failure to Pay, Restructuring, Repudiation/Moratorium, Governmental Intervention; FDIA 12 U.S.C. § 1821(c)) and SEC Form 8-K Item 1.05. Bankruptcy/receivership/regulatory seizure sets severity floor >= 8; failure to pay/bank run/capital loss/material cyber sets severity floor >= 7. Entity must be verified subject; conference/sponsorship uses excluded. | `sentinel.nlp.credit_terms`, `sentinel.nlp.events`, `sentinel.nlp.severity` |

## Module B (Wholesale & Retail Stress Testing)

| Assumption | Value / Rule | Where |
|---|---|---|
| **Wholesale book construction** | Issuers: the 2 largest debt issuers per GICS sector among S&P 100 constituents with a 10-K balance sheet dated 2024-06-30 or later (20 issuers, 11 sectors). Every figure comes from the latest fiscal year, with the XBRL tag recorded per issuer; issuers with a large captive lender (GM, F, DE, CAT; listed because XBRL has no standard flag for it) are excluded because consolidated interest coverage is not meaningful; an issuer with no positive interest-expense fact for the year (AAPL) gets a stated BBB default; the basis of every rating is recorded per issuer. Synthetic rating from interest coverage (Damodaran large-firm table) for non-financials and equity/assets for financials. Baseline PD (S&P 2020 study, Table 3): AAA 0.00%, AA 0.02%, A 0.05%, BBB 0.16%, BB 0.63%, B 3.34%, CCC/C 28.30%. LGD 45% (Basel F-IRB senior unsecured). Baseline bond spread = latest FRED ICE BofA OAS of the rating bucket. Sizing $EAD_i \propto \sqrt{\text{debt}_i}$, 8% single-name cap, $80M cash. Positions are synthetic (`is_synthetic: true`). | `scripts/data/build_wholesale_book.py`, `data/portfolio/wholesale_real.json` |
| **Spread calibration** | Index spread change from a credit ETF hedged with IEF at matched duration: $\Delta s = -(r_{credit} - (D_c/D_{IEF})\, r_{IEF})/D_c$, with $D_{HYG}=3.7$, $D_{LQD}=8.4$, $D_{IEF}=7.3$. Sensitivity to ±0.5 years on each duration is stored per window in `data/market/stress_windows.json`. Checked against FRED ICE BofA OAS where FRED has history (Fed pivot 2023: HY -89.5 bp implied vs -100 bp actual; IG -37.4 vs -29 bp). | `sentinel.stress.calibration`, `scripts/data/calibrate_shocks.py` |
| **Bond spread valuation** | $\Delta P \approx -D_{spread} \cdot \Delta s \cdot P$ where spread widening ($\Delta s > 0$) lowers market value. Modified duration: $D = \frac{1 - (1+y)^{-T}}{y}$ with yield $y = y_{treasury} + s_{OAS}$. Parallel spread shift assumption ($D_{spread} = D_{modified}$). | `sentinel.stress.valuation` |
| **Loan credit triangle & PD mapping** | $\Delta PD_i = m(\text{rating}_i)\, \Delta s / LGD_i$, so $\Delta ECL_i = EAD_i \cdot m_i \cdot \Delta s$ (independent of LGD). Used for systemic scenarios; single-name shocks use an explicit PD increment, also scaled by $m$. | `sentinel.stress.valuation` |
| **Risk-neutral vs physical PD note** | Spread shock represents risk-neutral default intensity shift ($\Delta \lambda \approx \Delta s / (1 - R)$). Historical physical PDs anchor baseline ECL; stressed ECL incorporates the market-implied spread distress to capture balance-sheet credit migration under regulatory stress testing guidelines. | `sentinel.stress.valuation` |
| **No provision release** | In market-easing or positive sentiment rallies ($\Delta s < 0$), incremental loan credit loss is floored at 0 ($\Delta ECL \le 0 \implies \Delta ECL = 0$). Regulatory provisions cannot be released into P&L from temporary sentiment rallies (conservatism principle under CECL/IFRS 9). Bonds recognize full mark-to-market appreciation. | `sentinel.stress.valuation` |
| **Rating multipliers** | $m$: AAA 0.20, AA 0.28, A 0.36, BBB 0.55, BB 0.75, B 1.10, CCC 1.90, applied to index spread moves and to PD increments (not to Treasury yield moves). Anchors: the HY index mix (50% BB, 38% B, 12% CCC) averages ~1.0 and the IG mix (5% AA, 45% A, 50% BBB) ~0.45, close to the measured median LQD/HYG spread-move ratio of 0.41. Off for the custom (explicit) stress unless requested. | `sentinel.stress.ratings`, `sentinel.stress.valuation` |
| **M&A shocks** | Applied strictly to the acquirer entity (reflecting post-merger debt issuance and execution friction). Scaled by consideration structure: $\times 1.5$ for debt-financed acquisitions, $\times 0.5$ for all-stock transactions. Targets do not take unsolicited credit deterioration shocks. | `sentinel.stress.shocks` |
| **Sector normalization** | All portfolio assets and shock targets normalize strictly to the 11 standard GICS sectors (`Communication Services`, `Consumer Discretionary`, `Consumer Staples`, `Energy`, `Financials`, `Health Care`, `Industrials`, `Information Technology`, `Materials`, `Real Estate`, `Utilities`) plus Non-Corporate (`Rates`, `Government / Cash`). Aliases resolve deterministically via `sentinel.stress.sectors.normalize_sector`. Scope matching uses strict equality. | `sentinel.stress.sectors`, `sentinel.stress.valuation` |
| **Contagion method** | Edges are same-GICS-sector residual return correlations ex-SPY over the last 252 trading days of `close_sp500.parquet` (2023-03-01 to 2024-02-29), kept if $\rho \ge 0.35$, at most 5 per name, transmission $\min(0.8, 0.9\rho)$. Up to 2 hops with decay 0.6 per hop, on single-name CREDIT and SUPPLY_CHAIN events. Names without price history (SIVB, FRC, SBNY) have no edges. No customer/supplier links are modelled. | `sentinel.stress.contagion` |
| **Retail/SME sleeve** | EAD = total debt + 30% CCF on credit-card limits; PD by FICO score bucket; LGD = 80% unsecured; scaled to $50M portfolio. Sector mapped to borrower's largest MCC spend category. | `scripts/data/build_credit_sleeve.py` |
| **Equity sleeve** | 15 S&P 100 constituents ($4M each, $60M total); beta and vol estimated from 252 days of real historical returns. | `scripts/data/build_equity_sleeve.py` |
| **CYBER operational loss** | 10x observed card-fraud rate of the victim's GICS sector, applied to retail tranches within that sector. | `sentinel.stress.valuation` |
| **Interest rate swaps & cash** | Swaps valued via signed $DV01 \times \Delta y$; cash balance unchanged under stress. | `sentinel.stress.valuation` |
| **Synthetic CET1 capital base** | Synthetic Tier 1 capital base is set to $85.0M for the $610M wholesale book (Standardized RWA $408.8M), yielding a baseline CET1 ratio of 13.82% (comfortably above the 8.0% Basel III minimum capital floor + capital conservation buffer). Stated on screen and in reports. | `sentinel.stress.staging`, `docs/assumptions.md` |
| **IFRS 9 loan staging & EAD vs ECL** | Exposure at Default (EAD) and Expected Credit Loss (ECL) are tracked and displayed separately. Baseline wholesale loan portfolio has $264.4M EAD ($262.8M Stage 1 performing, $1.6M Stage 3 defaulted) and $2.66M ECL ($1.38M Stage 1 12-month ECL, $1.28M Stage 3 lifetime ECL). Invariant $ECL < EAD$ is verified across all staging migrations. | `sentinel.stress.staging`, `sentinel.api.routes.stress` |
| **Reverse stress testing** | Solves via bisection for the minimum scenario shock multiplier $\lambda$ that breaches the regulatory 8.0% CET1 floor using the real multi-asset stress valuation engine. Verified by test that $\lambda$ breaches and $\lambda - \text{tolerance}$ does not. | `sentinel.stress.staging`, `sentinel.stress.engine` |
| **Early-Warning Watchlist** | Internal multi-factor early-warning monitoring watchlist (composite score combining financial metrics, debt structure, and external risk signals into GREEN/AMBER/RED status). Does not imply Crisil affiliation. | `sentinel.stress.ews`, `sentinel.stress.engine` |

## Module A (Index Rebalancer)

| Assumption | Value | Where |
|---|---|---|
| **Universe** | 20 S&P 100 names with the best tweet coverage, equal base weights (5% each) | `sentinel.rebalance.engine` |
| **Sentiment EMA** | Alpha = 0.3 per signal, half-life 5 trading days | `sentinel.rebalance.engine` |
| **No-trade band** | 25 bps (0.0025); trades skipped if \|target_weight - current_weight\| < band | `sentinel.rebalance.engine` |
| **Weight constraints** | Long-only, single-name cap $\le 20\%$, GICS sector cap $\le 40\%$ | `sentinel.rebalance.engine` |
| **Transaction costs & break-even** | Turnover evaluated at 0 bps, 5 bps, and 10 bps linear execution costs. Break-even cost = active annual return / annual turnover. Circular moving-block bootstrap (fixed 20-day blocks, 2,000 resamples) gives 95% confidence intervals. | `sentinel.rebalance.engine`, `scripts/backtest_module_a.py` |

## Runtime & Compliance

- **Zero External Network Calls**: The backend makes strictly zero network requests during runtime. Validated on every commit by `scripts/verify_hygiene.py`.
- **Local Recording**: Real-time ingest runs out-of-process via `scripts/live/record_live.py`, appending to local files parsed by the engine.
- **Holdout labels**: the 120-row real-news holdout (`data/eval/holdout_v2_news.csv`) was labeled in one pass by an AI agent, not by a person, and has not been reviewed. It is independent of the repository's models but is not human ground truth; `holdout_v2_news.provenance.json` records this and how to replace it with human labels.
