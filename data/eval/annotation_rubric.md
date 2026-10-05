# Financial Event & Severity Annotation Rubric

This document defines the standardized ground-truth annotation rubric for NLP model evaluation in S&P Sentinel, conforming to PRD Section 8.

---

## 1. Supported Event Taxonomy (9 Classes + OTHER)

| Event Class | Definition & Trigger Evidence | Example Phrases |
|---|---|---|
| `CREDIT` | Rating downgrades, missed coupons, covenant breaches, default, debt restructuring | "missed payment", "covenant breach", "downgraded to BB", "debt restructuring" |
| `MACRO` | Central bank rate decisions, sovereign yield shifts, inflation prints, GDP reports | "interest rate hike", "PPI surged", "yield curve inversion", "ECB liquidity" |
| `SUPPLY_CHAIN` | Port bottlenecks, factory force majeure, shipping halts, raw material deficits | "blast furnace fire", "freight strike", "container backlog", "force majeure" |
| `REGULATORY` | Antitrust inquiries, SEC probes, FTC injunctions, regulatory fines, compliance mandates | "antitrust probe", "SEC inquiry", "FTC injunction", "monopoly suit" |
| `EARNINGS` | Quarterly revenue/profit beats, misses, guidance cuts, margin compression | "earnings surged", "guidance lowered", "net income beat", "margin contraction" |
| `M_AND_A` | Mergers, acquisitions, tender offers, spin-offs, hostile takeovers | "all-cash acquisition", "definitive buyout agreement", "hostile bid" |
| `CYBER` | Ransomware attacks, unpatched zero-day exploits, corporate network breaches | "ransomware attack", "unpatched CVE", "unauthorized encryption", "data breach" |
| `PRODUCT` | FDA regulatory drug approvals, major product rollouts, patent awards | "FDA priority approval", "Phase 3 clinical success", "activated subsea cable" |
| `GEOPOLITICAL` | Cross-border trade sanctions, military conflicts, maritime corridor blockades | "naval skirmish in Hormuz", "trade talks collapsed", "export tariff dispute" |
| `OTHER` | General business commentary, executive appointments, non-material news | "appointed new COO", "headquarters relocation", "annual shareholder meeting" |

---

## 2. Impact Severity Rubric (Integer Scale 1 to 10)

Calculated via transparent additive components:

$$\text{Impact Score} = \min\left(10, \max\left(1, \text{Base Score} + \text{Scope Increment} + \text{Severity Increment}\right)\right)$$

### Step 1: Event Base Score (1 to 6)
- **Base 5:** Evidenced default, bankruptcy filing, sovereign emergency rate action (`CREDIT`, `MACRO`).
- **Base 4:** Rating agency downgrade warning, production plant shutdown (`SUPPLY_CHAIN`, `CYBER`).
- **Base 3:** Regulatory injunction, quarterly earnings miss > 15%, antitrust probe (`REGULATORY`, `EARNINGS`).
- **Base 2:** Ordinary quarterly earnings announcement, routine M&A announcement (`M_AND_A`, `PRODUCT`).
- **Base 1:** Non-material operational update, executive transition (`OTHER`).

### Step 2: Scope Increment (0 to 2)
- **+0 (Isolated):** Single business division or small subsidiary affected.
- **+1 (Firm-Wide / Sector):** Affects the entire parent entity, or triggers spillover to direct sector peers.
- **+2 (Systemic):** Affects core financial clearing, sovereign rates, or multiple critical supply chains.

### Step 3: Explicit Severity Multiplier (0 to 2)
- **+0:** Exploratory rumors, preliminary inquiries, or unconfirmed commentary.
- **+1:** Formal regulatory filing (SEC 8-K, formal notice) or verified operational stoppage.
- **+2:** Missed payment, immediate credit covenant breach, or irreversible business cessation.

---

## 3. Authorship & Licensing

- **Author:** Aman Gupta (Indian Institute of Technology Kharagpur)
- **License:** MIT License (Project-Authored Evaluation Rubric, consistent with repository root `LICENSE`)
- **Provenance Notice:** Conforms to `data/DATA_LICENSE.md`. Contains zero confidential or proprietary criteria from S&P Global or CRISIL.

