# Financial & Quantitative Modeling Assumptions

**Repository:** S&P Sentinel — Financial Text Risk Intelligence & Wholesale Portfolio Stress Platform  
**Author:** Aman Gupta (Indian Institute of Technology Kharagpur)  
**Standard Compliance:** IFRS 9 Incremental Expected Credit Loss (ECL), ISDA Standard Fixed-Income Pricing, and Network Risk Propagation  

---

## 1. Wholesale & Retail Portfolio Composition

The balance sheet under surveillance comprises an institutional **$500,000,000 USD Wholesale Banking Portfolio** alongside an aggregated **$50,000,000 USD Consumer & SME Retail Credit Sleeve**:

### 1.1 Wholesale Banking Book ($500M Funded + $150M Derivative Notional)
The wholesale portfolio (`data/wholesale_positions.json`) models an institutional balance sheet across four segregated asset classes:

1. **Corporate Syndicated Loans ($220,000,000 USD):**
   - **Accounting Treatment:** Held at amortized cost in the institutional banking book under IFRS 9 single-period accounting conventions.
   - **Composition:** 5 distinct funded facilities across Industrials (`APEX`), Transportation (`GLOG`), Technology (`QSEM`), Energy (`SLEN`), and Steel (`TSTEL`).
   - **Credit Risk Parameters:** Baseline Probability of Default ($PD_{\text{base}}$) ranging from $0.8\%$ to $2.5\%$, and Loss Given Default ($LGD$) from $30\%$ to $45\%$.
   - **Clamping Guarantee:** Stressed Probability of Default is strictly clamped to the closed interval $[0.0, 1.0]$.

2. **Corporate Fixed-Rate Bonds ($200,000,000 USD):**
   - **Accounting Treatment:** Mark-to-market (MTM) traded securities under trading book conventions.
   - **Composition:** 5 senior unsecured bullet notes maturing between 2028 and 2033.
   - **Duration & Spread:** Modified duration ($D_{\text{mod}}$) ranges from $3.6$ to $6.2$ years (portfolio weighted average $\approx 4.6$ years). Baseline credit spreads range from $110$ to $280$ bps over benchmark sovereign curves.

3. **SOFR Bilateral Interest Rate Swaps ($150,000,000 USD Gross Notional):**
   - **Accounting Treatment:** Centrally cleared bilateral OTC derivatives referencing USD Secured Overnight Financing Rate (SOFR).
   - **Balance Sheet Segregation:** Derivative gross notional is strictly segregated from funded book value, preventing artificial double-counting of funded assets.
   - **Valuation Baseline:** MTM initialized to $\$0.00$ USD (at-the-market par swaps at trade inception).
   - **Signed DV01 (Dollar Value of an 01):** Measures dollar P&L sensitivity per 1 basis point ($+0.01\%$) parallel shift in benchmark yields:
     - `SWAP-001` (Receive-Fixed 5Y, \$100M notional): Negative DV01 ($-\$42,000\text{ USD/bp}$). Incurs MTM loss under rate hikes; gains under rate cuts.
     - `SWAP-002` (Pay-Fixed 3Y, \$50M notional): Positive DV01 ($+\$12,500\text{ USD/bp}$). Gains under rate hikes; incurs MTM loss under rate cuts.

4. **Cash & Sovereign Treasury Reserves ($80,000,000 USD):**
   - Overnight risk-free liquidity reserves held at the Federal Reserve Bank.
   - Zero interest rate duration ($D_{\text{mod}} = 0.0$), zero credit default risk ($PD = 0.0$, AAA rating). Yield: 5.25% annualized.

### 1.2 Consumer & SME Retail Credit Sleeve ($50M Funded EAD)
To satisfy Hackathon Problem Statement Module B ("provided sample transaction data") per Review Plan §6.4, an empirical retail credit sleeve (`data/portfolio/credit_sleeve.csv`) is derived from public Kaggle transaction and debt analytics:
- **Source Ingestion:** Ingests user credit scores, outstanding debt balances, and dominant Merchant Category Codes (MCC).
- **Rating Bucketing:** Maps FICO/credit score to supervisory rating buckets:
  - $\text{Score} \ge 760 \implies \text{AA}$ ($PD_{\text{base}} = 0.5\%$)
  - $700 \le \text{Score} < 760 \implies \text{BBB}$ ($PD_{\text{base}} = 1.5\%$)
  - $640 \le \text{Score} < 700 \implies \text{BB}$ ($PD_{\text{base}} = 4.0\%$)
  - $\text{Score} < 640 \implies \text{B-}$ ($PD_{\text{base}} = 10.0\%$)
- **Sector Mapping:** Dominant MCC codes map to 8 industrial sectors (e.g. `5411` Consumer Staples, `5541` Energy, `4511` Industrials/Airlines, `5732` Technology).
- **Unsecured Recovery:** $LGD = 0.80$ reflecting unsecured revolving credit.
- **Pooled Loan Positions:** Aggregated into 8 pooled loan tranches ($RTL\_SECT\_RATING$) scaling to $\$50,000,000$ USD total Exposure at Default (EAD).

---

## 2. Quantitative Valuation & Stress Formulas (Module B)

### 2.1 Loan Portfolio — Expected Credit Loss (ECL) Shock
For syndicated corporate loans and pooled retail credit tranches, risk is quantified via 1-year incremental Expected Credit Loss:

$$\Delta \text{ECL} = \Delta \text{PD} \times \text{LGD} \times \text{EAD}$$

$$\text{Stressed PD} = \min\left(1.0, \max\left(0.0, \text{PD}_{\text{base}} + \Delta \text{PD}\right)\right)$$

$$\text{Loan P\&L} = -\Delta \text{ECL}$$

Where:
- $\text{EAD}$: Exposure at Default (total funded facility balance).
- $\Delta \text{PD}$: Additive default probability shock calibrated to NLP impact severity and scenario shocks:
  $$\Delta \text{PD} = \text{PD}_{\text{base}} \times \left(\frac{\text{Severity}}{10}\right) \times \text{Scale Factor}$$
- $\text{LGD}$: Loss Given Default (unsecured shortfall percentage).

### 2.2 Corporate Bond Portfolio — Modified Duration & Convexity
Price revaluation incorporates both first-order modified duration and second-order convexity adjustments under credit spread widening ($\Delta s$) and benchmark yield moves ($\Delta y$):

$$\frac{\Delta P}{P} \approx -D_{\text{mod}} \times (\Delta y + \Delta s) + \frac{1}{2} C \times (\Delta y + \Delta s)^2$$

$$\text{Bond P\&L} = \text{Market Value} \times \frac{\Delta P}{P}$$

Where:
- $D_{\text{mod}}$: Modified duration in years.
- $C$: Bond convexity in $\text{years}^2$ ($C \approx D_{\text{mod}} \times (D_{\text{mod}} + 1)$).
- $\Delta s$: Change in issuer credit spread in decimal (e.g. $+150\text{ bps} \implies +0.0150$).
- $\Delta y$: Change in benchmark sovereign yield in decimal (e.g. $+100\text{ bps} \implies +0.0100$).

### 2.3 Interest Rate Swaps — Signed DV01 Curve Shocks
Derivative mark-to-market shifts under yield curve shifts are evaluated via signed DV01:

$$\text{Swap P\&L} = \text{Signed DV01} \times \Delta y_{\text{bp}}$$

Where:
- $\Delta y_{\text{bp}}$: Yield curve shift expressed in basis points ($1\text{ bp} = 0.01\%$).
- **Receive-Fixed Swap:** $\text{Signed DV01} < 0$. Incurs losses when yields rise; gains when yields fall.
- **Pay-Fixed Swap:** $\text{Signed DV01} > 0$. Gains when yields rise; incurs losses when yields fall.

### 2.4 Systemic Macro Curve Shifts & Rate Cut Handling
Macroeconomic rate shocks (`MACRO` event class or `rate_shock` scenario) apply systemic curve shifts across the balance sheet:
- **Parallel Curve Transmission:** Shifts apply across sovereign benchmark yields ($\Delta y_{\text{bp}}$), repricing all corporate bonds and interest rate swaps simultaneously.
- **Directional Consistency:** Rate hikes ($\Delta y > 0$) reduce bond prices and hurt receive-fixed swaps while benefiting pay-fixed swaps. Rate cuts ($\Delta y < 0$) increase bond prices and benefit receive-fixed swaps while hurting pay-fixed swaps.

---

## 3. Contagion Graph & Risk Propagation

### 3.1 Network Topology & Transmission Weights
Second-order risk propagation is modeled using a directed NetworkX graph (`data/graph_edges.csv`):
- **Customer-Supplier Links:** Upstream supplier disruptions propagate to dependent customers with weight $0.40 \le w_{ij} \le 0.75$ (e.g. `APEX` $\to$ `TSTEL` at $0.45$; `TSTEL` $\to$ `VAUTO` at $0.65$).
- **Debtor-Creditor Links:** Counterparty credit defaults propagate to exposed financial counterparties with weight $0.30 \le w_{ij} \le 0.60$ (e.g. `APEX` $\to$ `GLOG` at $0.35$).

### 3.2 Multi-Hop Bounded Damping
To prevent artificial systemic runaway feedback loops:
1. **Hop Limitation:** Propagation is strictly bounded to a maximum of **2 hops**.
2. **Geometric Distance Damping:** Transmission dampens exponentially with distance:
   $$\text{Hop Factor}(h) = \left(\prod_{k=1}^h w_k\right) \times 0.50^h$$
3. **Isolated Node Protection:** Entities without graph edges (e.g. `QSEM`, `SLEN`) remain completely insulated from non-systemic counterparty shocks ($\text{Contagion Factor} = 0.0$, $\text{P\&L} = \$0$).
4. **Cycle Suppression:** Visited node tracking prevents infinite loops in bidirectional relationships.

---

## 4. Replay Deduplication & Temporal Window Assumptions

1. **24-Hour Rolling Temporal Window:** Financial media outlets frequently publish syndicated news wire echoes or re-tweet rumors over rolling 24-hour periods.
2. **Dual-Mode Deduplication:**
   - **Exact Hash Matching:** SHA-256 hash of canonical content string suppresses exact duplicates.
   - **Token Jaccard Similarity ($\ge 0.65$):** Suppresses near-duplicate wire copy with minor phrasing edits.
   - **Sub-Phrase Containment ($\ge 0.80$):** Suppresses condensed headlines or snippets contained within longer wire stories.
3. **Action Gating:** Subsequent duplicate signals within 24 hours are recorded in the audit trail with `action_blocked: true`, preventing redundant compounding balance sheet shocks.

---

## 5. NLP Feature Extraction Assumptions

1. **Entity Linking Spans:** True character start/end offsets (`[start, end]`) are extracted directly from the input text, grounding signals without synthetic text truncations.
2. **Sentiment Normalization:** FinBERT probabilities satisfy the mathematical axiom:
   $$P(\text{positive}) + P(\text{negative}) + P(\text{neutral}) = 1.0 \pm 0.001$$
   $$\text{Continuous Polarity} = P(\text{positive}) - P(\text{negative}) \in [-1.0, +1.0]$$
3. **10-Class Event Taxonomy with Abstention:** Event categorization defaults to `OTHER` whenever model classification confidence falls below $0.40$, avoiding false alarm systemic shocks.
4. **Additive Severity Rubric:**
   $$\text{Severity} = \min\left(10, \max\left(1, \text{Base Severity} + \text{Scope Modifier} + \text{Dynamic Multipliers}\right)\right)$$
   Where dynamic multipliers account for regulatory enforcement fines ($>\$100\text{M}$), facility shutdowns, and capital expenditure revisions.

---

## 6. Offline Localhost Security & Governance

1. **Zero External Network Dependencies:** Runtime execution operates strictly on `127.0.0.1` / `localhost` with zero external HTTP requests to cloud LLMs or third-party market data APIs.
2. **Cryptographic Data Provenance:** All 15 bundled datasets are cataloged in `data/manifest.json` with SHA-256 hashes and byte lengths verified by `scripts/verify_hygiene.py`.
3. **Confidentiality Assurance:** Zero non-public, proprietary, or client-confidential data from S&P Global or CRISIL is incorporated, satisfying Hackathon Guidelines Sections 8 and 9.
