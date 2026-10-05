# Financial & Quantitative Modeling Assumptions

This document formally records all financial modeling conventions, mathematical approximations, and engineering assumptions governing **S&P Sentinel**.

---

## 1. Wholesale Portfolio Composition & Accounting Standards

The synthetic institutional portfolio (`data/wholesale_positions.json`) models a $500,000,000 USD balanced wholesale credit and rates book across four distinct asset classes:

1. **Corporate Syndicated Loans ($220,000,000 USD):**
   - Book Value: Held at amortized cost under institutional banking book conventions.
   - 5 distinct counterparty facilities across Industrials, Transportation, Technology, and Energy sectors.
   - Credit Risk Metrics: Probability of Default (PD) ranging from 0.8% to 2.5%, and Loss Given Default (LGD) from 30% to 45%.

2. **Corporate Bonds ($200,000,000 USD):**
   - Fair Value: Mark-to-market (MTM) traded securities under trading book conventions.
   - 5 senior unsecured bullet notes with maturities between 2028 and 2033.
   - Average modified duration: ~4.6 years (range 3.6 to 6.2 years).
   - Baseline credit spreads: 110 to 280 bps over benchmark yields.

3. **Interest Rate Swaps ($150,000,000 USD Gross Notional):**
   - Centrally cleared bilateral OTC derivatives referencing USD Secured Overnight Financing Rate (SOFR).
   - Baseline MTM: $0.00 USD (at-market par swaps at inception).
   - Signed DV01 (Dollar Value of a 01): Measures portfolio P&L sensitivity per 1 basis point (+0.01%) parallel shift in benchmark yields.
   - Position 1 (`SWAP-001`): Receive-fixed 5-year swap, negative DV01 (-$42,000 USD/bp).
   - Position 2 (`SWAP-002`): Pay-fixed 3-year swap, positive DV01 (+$12,500 USD/bp).

4. **Cash & Sovereign Treasury Reserves ($80,000,000 USD):**
   - Overnight liquid reserves held at the Federal Reserve Bank.
   - Zero duration ($D_{\text{mod}} = 0.0$), zero credit risk ($PD = 0.0$, AAA rating).
   - Yield: 5.25% annualized.

---

## 2. Quantitative Stress Valuation Formulas (Module B)

### 2.1 Loan Portfolio — Expected Credit Loss (ECL) Shock
When an issuer experiences an adverse credit event or macroeconomic downturn, the loan loss is modeled through the change in 1-year Expected Credit Loss:

$$\Delta \text{ECL} = \Delta \text{PD} \times \text{LGD} \times \text{EAD}$$

Where:
- $\Delta \text{PD}$: The additive shock to the counterparty's Probability of Default (e.g., $+0.025$ or $+250 \text{ bps}$).
- $\text{LGD}$: Loss Given Default (percentage recovery shortfall).
- $\text{EAD}$: Exposure at Default (total funded facility amount).

### 2.2 Corporate Bond Portfolio — Modified Duration & Spread Shocks
The first-order price change resulting from credit spread blowout ($\Delta s$) or benchmark rate shock ($\Delta y$) is evaluated using modified duration:

$$\frac{\Delta P}{P} \approx -D_{\text{mod}} \times (\Delta y + \Delta s)$$

$$\text{Bond P\&L} = \text{Market Value} \times \left(-D_{\text{mod}} \times (\Delta y + \Delta s)\right)$$

Where:
- $D_{\text{mod}}$: Modified duration in years.
- $\Delta y$: Change in benchmark sovereign yield (in decimal, e.g., $+0.0100$ for $+100 \text{ bps}$).
- $\Delta s$: Change in issuer credit spread (in decimal, e.g., $+0.0150$ for $+150 \text{ bps}$).

### 2.3 Interest Rate Swaps — Signed DV01 Curve Shocks
Derivative mark-to-market shifts under yield curve shocks are approximated via signed DV01:

$$\text{Swap P\&L} = \text{Signed DV01} \times \Delta y_{\text{bp}}$$

Where:
- $\Delta y_{\text{bp}}$: Yield shift expressed in basis points (e.g., $+100$ for a 100 bps rate surge).
- A receive-fixed swap has negative DV01, incurring a loss when rates rise.
- A pay-fixed swap has positive DV01, gaining when rates rise.

---

## 3. Contagion Graph & Risk Propagation Assumptions

1. **Topology:** Directed dependency edges (`data/graph_edges.csv`) model asymmetric transmission:
   - Upstream supplier disruption propagates to downstream customer with transmission factor $0.40 \le \tau \le 0.75$.
   - Major customer credit failure propagates to dependent supplier with transmission factor $0.30 \le \tau \le 0.60$.
2. **Hop Limitation:** Contagion propagation is bounded to a maximum of **2 hops** to avoid runaway compounding.
3. **Decay Factor:** A spatial damping coefficient $\delta = 0.50$ is applied per hop:

$$\text{Second-Order Impact} = \text{Source Severity} \times \tau_{ij} \times \delta$$

---

## 4. Replay Deduplication Window Assumptions

1. **24-Hour Entity Deduplication:** Financial news outlets frequently re-report identical credit events with slight phrasing variations.
2. **Suppression Logic:** If an actionable event ($Impact \ge 7$) for entity $E$ and event class $C$ occurs within 24 hours of an already-processed signal, subsequent signals are flagged as duplicates and suppressed from applying cumulative secondary portfolio shocks.

---

## 5. Offline Runtime Policy Assumptions

1. **Localhost Isolation:** All computation occurs strictly on `127.0.0.1` / `localhost`.
2. **Zero External APIs:** No calls to OpenAI, Anthropic, Hugging Face Hub (at runtime), or external news services.
3. **Zero Proprietary Secrets:** The platform operates with zero API tokens or cloud credentials.
